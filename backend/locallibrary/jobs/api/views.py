import json

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
        nl_prompt = request.POST.get("nl_prompt") or request.POST.get("natural_language_prompt", "")
        pattern = request.POST.get("pattern", "")
        replacement = request.POST.get("replacement", "")
        target_columns = request.POST.get("target_columns", "")
        engine = request.POST.get("engine", "spark")

        # If no explicit pattern provided but NL prompt exists, generate regex
        if not pattern and nl_prompt:
            try:
                regex_payload = generate_regex_from_prompt(nl_prompt)
                pattern = regex_payload.get("pattern", "")
            except Exception:
                pattern = ""

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
            try:
                uploaded.close()
            except Exception:
                pass

        job = data.create_job(
            input_text=sample_text,
            pattern=pattern,
            replacement=replacement,
            natural_language_prompt=nl_prompt,
            uploaded_file="",
            target_columns=target_columns,
        )

        # save uploaded file to MEDIA_ROOT/uploads/job_<id>/
        from django.conf import settings
        import os

        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads", f"job_{job.id}")
        os.makedirs(upload_dir, exist_ok=True)
        filename = uploaded.name
        dest_path = os.path.join(upload_dir, filename)
        with open(dest_path, "wb") as dst:
            uploaded.open("rb")
            for chunk in uploaded.chunks():
                dst.write(chunk)
            uploaded.close()

        # store file path on job
        Job = None
        try:
            from jobs.models import Job as JobModel
            JobModel.objects.filter(id=job.id).update(uploaded_file=dest_path)
        except Exception:
            # fallback: update via data layer if available
            data.get_job(job.id).uploaded_file = dest_path
            data.get_job(job.id).save(update_fields=["uploaded_file"])

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
    # Basic row extraction: split into lines. For tabular/CSV results this
    # should be replaced with structured parsing or reading stored files.
    if "\n" in output_text:
        lines = output_text.splitlines()
    elif output_text == "":
        lines = []
    else:
        lines = [output_text]

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

    total = len(lines)
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
    page_lines = lines[start:end]

    rows = [{"output_text": l} for l in page_lines]
    columns = ["output_text"]

    return JsonResponse({"rows": rows, "columns": columns, "total_pages": total_pages, "page": page})
