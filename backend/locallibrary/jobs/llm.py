import json
import os
import re


def generate_regex_from_prompt(prompt):
    if not os.getenv("OPENAI_API_KEY"):
        return _fallback_regex(prompt)

    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only JSON with keys pattern, replacement, and explanation. "
                    "The pattern must be a valid Python regular expression."
                ),
            },
            {
                "role": "user",
                "content": f"Create a regex replacement plan for: {prompt}",
            },
        ],
    )
    payload = json.loads(response.choices[0].message.content)
    return _normalize_regex_payload(payload, source="openai")


def _fallback_regex(prompt):
    lowered = prompt.lower()
    if "email" in lowered:
        payload = {
            "pattern": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "replacement": "[EMAIL]",
            "explanation": "Fallback pattern for matching email addresses.",
        }
    elif "phone" in lowered:
        payload = {
            "pattern": r"\+?\d[\d\s().-]{7,}\d",
            "replacement": "[PHONE]",
            "explanation": "Fallback pattern for matching phone-like numbers.",
        }
    elif "number" in lowered or "digit" in lowered:
        payload = {
            "pattern": r"\d+",
            "replacement": "#",
            "explanation": "Fallback pattern for matching digit runs.",
        }
    else:
        payload = {
            "pattern": r".+",
            "replacement": "",
            "explanation": "Fallback catch-all pattern because no API key is configured.",
        }
    return _normalize_regex_payload(payload, source="fallback")


def _normalize_regex_payload(payload, *, source):
    pattern = str(payload.get("pattern", ""))
    replacement = str(payload.get("replacement", ""))
    explanation = str(payload.get("explanation", ""))
    re.compile(pattern)
    return {
        "pattern": pattern,
        "replacement": replacement,
        "explanation": explanation,
        "source": source,
    }
