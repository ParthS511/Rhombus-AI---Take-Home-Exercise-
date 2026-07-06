import json
import os
from hashlib import sha256

from django.core.cache import cache

from .regex_safety import validate_regex_safety


LLM_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7


def generate_regex_from_prompt(prompt):
    cache_key = _cache_key(prompt)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return {**cached_payload, "cached": True}

    config = _llm_config()
    if config is None:
        payload = _fallback_regex(prompt)
        cache.set(cache_key, payload, LLM_CACHE_TTL_SECONDS)
        return payload

    # Groq exposes an OpenAI-compatible API, so we use the OpenAI SDK client
    # with Groq's base URL instead of adding a second provider-specific package.
    from openai import OpenAI

    client_kwargs = {"api_key": config["api_key"]}
    if config["base_url"]:
        client_kwargs["base_url"] = config["base_url"]

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=config["model"],
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
    normalized_payload = _normalize_regex_payload(payload, source=config["source"])
    cache.set(cache_key, normalized_payload, LLM_CACHE_TTL_SECONDS)
    return normalized_payload


def _llm_config():
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        return {
            "api_key": groq_key,
            "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "source": "groq",
        }

    return None


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
    validate_regex_safety(pattern)
    return {
        "pattern": pattern,
        "replacement": replacement,
        "explanation": explanation,
        "source": source,
    }


def _cache_key(prompt):
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    digest = sha256(f"{model}:{prompt.strip().lower()}".encode("utf-8")).hexdigest()
    return f"llm_regex:{digest}"
