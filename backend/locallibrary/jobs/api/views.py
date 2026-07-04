import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from jobs.orchestration import RegexPatternError, apply_regex_replacement

from .serializers import RegexReplacementSerializer


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


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})


def _format_serializer_errors(errors):
    messages = []
    for field, field_errors in errors.items():
        joined_errors = " ".join(str(error) for error in field_errors)
        messages.append(f"{field}: {joined_errors}")
    return " ".join(messages)
