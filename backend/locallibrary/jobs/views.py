import json
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST


@csrf_exempt
@require_POST
def regex_replace(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    text = payload.get("text")
    pattern = payload.get("pattern")
    replacement = payload.get("replacement", "")

    if not isinstance(text, str):
        return JsonResponse({"error": "Field 'text' is required and must be a string."}, status=400)

    if not isinstance(pattern, str) or pattern == "":
        return JsonResponse({"error": "Field 'pattern' is required and must be a non-empty string."}, status=400)

    if not isinstance(replacement, str):
        return JsonResponse({"error": "Field 'replacement' must be a string."}, status=400)

    try:
        compiled_pattern = re.compile(pattern)
    except re.error as exc:
        return JsonResponse({"error": f"Invalid regex pattern: {exc}"}, status=400)

    matches = [
        {
            "match": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "groups": list(match.groups()),
        }
        for match in compiled_pattern.finditer(text)
    ]

    return JsonResponse(
        {
            "matches": matches,
            "match_count": len(matches),
            "result": compiled_pattern.sub(replacement, text),
        }
    )

@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})
