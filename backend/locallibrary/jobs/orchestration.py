import re

from . import data


class RegexPatternError(ValueError):
    pass


def apply_regex_replacement(*, text, pattern, replacement=""):
    try:
        compiled_pattern = re.compile(pattern)
    except re.error as exc:
        raise RegexPatternError(f"Invalid regex pattern: {exc}") from exc

    matches = [
        {
            "match": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "groups": list(match.groups()),
        }
        for match in compiled_pattern.finditer(text)
    ]

    return {
        "matches": matches,
        "match_count": len(matches),
        "result": compiled_pattern.sub(replacement, text),
    }


def run_regex_job(job_id, *, engine="python-re"):
    job = data.get_job(job_id)
    data.mark_running(job)

    try:
        payload = apply_regex_replacement(
            text=job.input_text,
            pattern=job.pattern,
            replacement=job.replacement,
        )
    except RegexPatternError as exc:
        data.mark_failed(job, str(exc))
        raise

    data.save_result(
        job=job,
        output_text=payload["result"],
        matches=payload["matches"],
        metadata={"engine": engine},
    )
    data.mark_succeeded(job)
    return payload
