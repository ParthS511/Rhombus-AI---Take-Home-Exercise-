import json
import csv
from io import StringIO

from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from jobs import data
from jobs.llm import generate_regex_from_prompt
from jobs.orchestration import RegexPatternError, apply_regex_replacement
from jobs.tasks import ping, process_regex_job, process_spark_regex_job

from .serializers import (
    JobCreateSerializer,
    JobSerializer,
    RegexGenerationSerializer,
    RegexReplacementSerializer,
)


@csrf_exempt
@require_POST
def regex_replace(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    serializer = RegexReplacementSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"error": _format_serializer_errors(serializer.errors)}, status=400)

    try:
        response_payload = apply_regex_replacement(**serializer.validated_data)
    except RegexPatternError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(response_payload)


@csrf_exempt
@require_POST
def generate_regex(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    serializer = RegexGenerationSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"error": _format_serializer_errors(serializer.errors)}, status=400)

    try:
        response_payload = generate_regex_from_prompt(serializer.validated_data["prompt"])
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(response_payload)


@csrf_exempt
@require_POST
def create_job(request):
    # Support both JSON and multipart/form-data uploads
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # multipart upload path (file + form fields)
    if request.FILES:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return JsonResponse({"error": "file: This field is required."}, status=400)

        nl_prompt = request.POST.get("nl_prompt") or request.POST.get("natural_language_prompt", "")
        pattern = request.POST.get("pattern", "")
        replacement = request.POST.get("replacement", "")
        target_columns = request.POST.get("target_columns", "")
        engine = request.POST.get("engine", "spark")

        if not pattern and not nl_prompt:
            return JsonResponse(
                {"error": "pattern: Provide a regex pattern or a natural language prompt."},
                status=400,
            )

        # Create job with a short preview of the uploaded file as input_text
        try:
            # read a small sample from the uploaded file for preview
            uploaded.open()
            sample_bytes = uploaded.read(4096)
            try:
                sample_text = sample_bytes.decode("utf-8", errors="replace")
            except Exception:
                sample_text = str(sample_bytes)
        finally:
            uploaded.seek(0)

        job = data.create_job(
            input_text=sample_text,
            pattern=pattern,
            replacement=replacement,
            natural_language_prompt=nl_prompt,
            target_columns=target_columns,
        )

        stored_name = default_storage.save(f"uploads/job_{job.id}/{uploaded.name}", uploaded)
        job.uploaded_file = default_storage.path(stored_name)
        job.save(update_fields=["uploaded_file", "updated_at"])

        # dispatch task (use spark engine by default for file uploads)
        task = process_spark_regex_job if engine == "spark" else process_regex_job
        async_result = task.delay(job.id)
        data.set_task_id(job.id, async_result.id)
        job.refresh_from_db()
        return JsonResponse(JobSerializer(job).data, status=202)

    # JSON path (original behavior)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    serializer = JobCreateSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"error": _format_serializer_errors(serializer.errors)}, status=400)

    validated_data = dict(serializer.validated_data)
    engine = validated_data.pop("engine")
    job = data.create_job(**validated_data)
    task = process_spark_regex_job if engine == "spark" else process_regex_job
    async_result = task.delay(job.id)
    data.set_task_id(job.id, async_result.id)
    job.refresh_from_db()

    return JsonResponse(JobSerializer(job).data, status=202)


@csrf_exempt
@require_POST
def ping_task(request):
    async_result = ping.delay()
    try:
        result = async_result.get(timeout=10)
    except Exception as exc:
        return JsonResponse(
            {"task_id": async_result.id, "error": str(exc)},
            status=504,
        )
    return JsonResponse({"task_id": async_result.id, "result": result})


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})


def _format_serializer_errors(errors):
    messages = []
    for field, field_errors in errors.items():
        joined_errors = " ".join(str(error) for error in field_errors)
        messages.append(f"{field}: {joined_errors}")
    return " ".join(messages)


@require_GET
def job_detail(request, job_id):
    try:
        job = data.get_job(job_id)
    except Exception:
        return JsonResponse({"error": "Job not found"}, status=404)

    return JsonResponse(JobSerializer(job).data)


@require_GET
def job_result(request, job_id):
    """Return a paginated view of the job result.

    For simple stored `Result.output_text`, this endpoint splits the output
    into lines and returns rows of a single `output_text` column. If the
    result metadata contains a `storage_path` or more structured data, that
    can be extended later to stream/parquet-read partitions.
    """
    try:
        job = data.get_job(job_id)
    except Exception:
        return JsonResponse({"error": "Job not found"}, status=404)

    if not hasattr(job, "result") or job.result is None:
        return JsonResponse({"rows": [], "columns": [], "total_pages": 0, "page": 1})

    output_text = job.result.output_text or ""
    rows, columns = _rows_from_result_text(output_text)

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get("page_size", 50))
    except ValueError:
        page_size = 50

    if page_size <= 0:
        page_size = 50

    total = len(rows)
    import math

    total_pages = math.ceil(total / page_size) if total else 0
    if total_pages == 0:
        return JsonResponse({"rows": [], "columns": [], "total_pages": 0, "page": page})

    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return JsonResponse({"rows": page_rows, "columns": columns, "total_pages": total_pages, "page": page})


def _rows_from_result_text(output_text):
    if not output_text:
        return [], []

    if "\n" in output_text:
        try:
            reader = csv.DictReader(StringIO(output_text))
            rows = list(reader)
            if reader.fieldnames and rows:
                return rows, reader.fieldnames
        except csv.Error:
            pass
        lines = output_text.splitlines()
    else:
        lines = [output_text]

    return [{"output_text": line} for line in lines], ["output_text"]
