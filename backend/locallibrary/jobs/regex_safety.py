import re


class UnsafeRegexError(ValueError):
    pass


def validate_regex_safety(pattern):
    if not pattern:
        raise UnsafeRegexError("Pattern must be a non-empty string.")
    if len(pattern) > 500:
        raise UnsafeRegexError("Regex pattern is too long.")
    if _has_nested_quantifier(pattern):
        raise UnsafeRegexError("Regex pattern contains nested quantifiers.")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise UnsafeRegexError(f"Invalid regex pattern: {exc}") from exc


def _has_nested_quantifier(pattern):
    # Conservative guard for common catastrophic-backtracking shapes, e.g. (a+)+.
    return bool(re.search(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)[+*{]", pattern))
