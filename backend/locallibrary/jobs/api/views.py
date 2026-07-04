import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from jobs import data
from jobs.orchestration import RegexPatternError, apply_regex_replacement
from jobs.tasks import process_regex_job

from .serializers import JobCreateSerializer, JobSerializer, RegexReplacementSerializer


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
def create_job(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    serializer = JobCreateSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"error": _format_serializer_errors(serializer.errors)}, status=400)

    job = data.create_job(**serializer.validated_data)
    async_result = process_regex_job.delay(job.id)
    data.set_task_id(job.id, async_result.id)
    job.refresh_from_db()

    return JsonResponse(JobSerializer(job).data, status=202)


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})


def _format_serializer_errors(errors):
    messages = []
    for field, field_errors in errors.items():
        joined_errors = " ".join(str(error) for error in field_errors)
        messages.append(f"{field}: {joined_errors}")
    return " ".join(messages)
