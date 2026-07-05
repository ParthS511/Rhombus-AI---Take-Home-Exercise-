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
