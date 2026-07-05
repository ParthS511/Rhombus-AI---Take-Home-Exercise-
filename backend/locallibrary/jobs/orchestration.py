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


def run_spark_regex_job(job_id):
    job = data.get_job(job_id)
    data.mark_running(job, progress=15)

    try:
        output_text = _apply_spark_regex(
            text=job.input_text,
            pattern=job.pattern,
            replacement=job.replacement,
        )
        payload = apply_regex_replacement(
            text=job.input_text,
            pattern=job.pattern,
            replacement=job.replacement,
        )
    except Exception as exc:
        data.mark_failed(job, str(exc))
        raise

    data.save_result(
        job=job,
        output_text=output_text,
        matches=payload["matches"],
        metadata={"engine": "spark-local"},
    )
    data.mark_succeeded(job)
    return {
        "matches": payload["matches"],
        "match_count": payload["match_count"],
        "result": output_text,
    }


def _build_spark_session():
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName("nl-regex")
        .master("local[*]")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def _apply_spark_regex(*, text, pattern, replacement):
    from pyspark.sql.functions import col, regexp_replace

    spark = _build_spark_session()
    try:
        dataframe = spark.createDataFrame([(text,)], ["input_text"])
        transformed = dataframe.withColumn(
            "output_text",
            regexp_replace(col("input_text"), pattern, replacement),
        )
        return transformed.select("output_text").first()["output_text"]
    finally:
        spark.stop()
