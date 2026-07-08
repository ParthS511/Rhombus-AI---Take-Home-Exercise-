import re
import os
from pathlib import Path

from . import data
from .llm import generate_regex_from_prompt
from .regex_safety import UnsafeRegexError, validate_regex_safety


class RegexPatternError(ValueError):
    pass


def apply_regex_replacement(*, text, pattern, replacement=""):
    try:
        _validate_regex_pattern(pattern)
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
    if job.status == job.Status.CANCELED:
        return {"canceled": True}
    data.mark_running(job)

    try:
        regex_metadata = _ensure_job_regex(job)
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
        metadata={"engine": engine, **regex_metadata},
    )
    data.mark_succeeded(job)
    return payload


def run_spark_regex_job(job_id):
    job = data.get_job(job_id)
    if job.status == job.Status.CANCELED:
        return {"canceled": True}
    data.mark_running(job, progress=15)
    try:
        regex_metadata = _ensure_job_regex(job)
        # If the job was created from an uploaded file, process the file with Spark
        if getattr(job, "uploaded_file", ""):
            output_path, sample_csv, rows_processed, columns = _apply_spark_regex_to_file(
                file_path=job.uploaded_file,
                pattern=job.pattern,
                replacement=job.replacement,
                target_columns=(job.target_columns or ""),
                job=job,
            )

            # create payload of matches from a sample text (best-effort)
            sample_text = sample_csv
            payload = apply_regex_replacement(
                text=sample_text,
                pattern=job.pattern,
                replacement=job.replacement,
            )

            metadata = {
                "engine": "spark-file",
                "storage_path": output_path,
                "rows": rows_processed,
                "columns": columns,
                **regex_metadata,
            }

            # Save sample CSV into output_text for quick preview
            data.save_result(
                job=job,
                output_text=sample_csv,
                matches=payload["matches"],
                metadata=metadata,
            )
        else:
            # fallback to single-string Spark transformation
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

            data.save_result(
                job=job,
                output_text=output_text,
                matches=payload["matches"],
                metadata={"engine": "spark-local", **regex_metadata},
            )

    except Exception as exc:
        data.mark_failed(job, str(exc))
        raise

    data.mark_succeeded(job)
    return {
        "matches": payload["matches"],
        "match_count": payload["match_count"],
        "result": payload.get("result", ""),
    }


def _build_spark_session(app_name="nl-regex"):
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName(app_name)
        .master(os.getenv("SPARK_MASTER", "local[1]"))
        .config("spark.ui.enabled", "false")
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "512m"))
        .config("spark.executor.memory", os.getenv("SPARK_EXECUTOR_MEMORY", "512m"))
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SQL_SHUFFLE_PARTITIONS", "1"))
        .getOrCreate()
    )


def _apply_spark_regex(*, text, pattern, replacement):
    from pyspark.sql.functions import col, regexp_replace

    _validate_regex_pattern(pattern)
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


def _apply_spark_regex_to_file(*, file_path, pattern, replacement, target_columns, job=None):
    """Read a CSV file with Spark, apply regexp_replace to target columns, write parquet output.

    Returns (output_path, sample_csv, rows_count, columns)
    """
    import csv
    from io import StringIO
    from pyspark.sql.functions import col, regexp_replace
    from django.conf import settings

    _validate_regex_pattern(pattern)
    source_path = Path(file_path)
    if not source_path.exists() and job and getattr(job, "input_text", ""):
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(job.input_text, encoding="utf-8")
    if not source_path.exists():
        raise FileNotFoundError(f"Uploaded file does not exist: {file_path}")

    spark = _build_spark_session("nl-regex-file")
    try:
        # Only CSV is supported for now; attempt to read with header and infer schema
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(file_path)

        all_columns = df.columns
        if target_columns:
            cols = [c.strip() for c in target_columns.split(",") if c.strip()]
            missing_columns = sorted(set(cols) - set(all_columns))
            if missing_columns:
                raise ValueError(
                    "Target columns not found in uploaded file: "
                    + ", ".join(missing_columns)
                )
        else:
            # choose string columns heuristically
            cols = [f.name for f in df.schema.fields if str(f.dataType).lower().startswith("string")]
            if not cols and all_columns:
                cols = [all_columns[0]]

        # apply regexp_replace to each target column
        for c in cols:
            if c in df.columns:
                df = df.withColumn(c, regexp_replace(col(c), pattern, replacement))

        # prepare output path
        output_dir = os.path.join(settings.MEDIA_ROOT, "results", f"job_{job.id}")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "data.parquet")

        # write parquet
        df.write.mode("overwrite").parquet(output_path)

        # sample first few rows for preview
        try:
            sample_df = df.limit(50).toPandas()
            sample_csv = sample_df.to_csv(index=False)
        except ModuleNotFoundError:
            sample_rows = df.limit(50).collect()
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=df.columns)
            writer.writeheader()
            for row in sample_rows:
                writer.writerow({col_name: row[col_name] for col_name in df.columns})
            sample_csv = output.getvalue()
        rows_count = df.count()

        # update job progress
        if job:
            data.mark_running(job, progress=80)

        return output_path, sample_csv, rows_count, df.columns
    finally:
        spark.stop()


def _validate_regex_pattern(pattern):
    try:
        validate_regex_safety(pattern)
    except UnsafeRegexError as exc:
        raise RegexPatternError(f"Invalid regex pattern: {exc}") from exc


def _ensure_job_regex(job):
    if job.pattern:
        return {}

    if not job.natural_language_prompt:
        raise RegexPatternError("A regex pattern or natural language prompt is required.")

    regex_payload = generate_regex_from_prompt(job.natural_language_prompt)
    job.pattern = regex_payload.get("pattern", "")
    if not job.replacement:
        job.replacement = regex_payload.get("replacement", "")
    job.save(update_fields=["pattern", "replacement", "updated_at"])
    _validate_regex_pattern(job.pattern)
    return {
        "regex_source": regex_payload.get("source", ""),
        "regex_explanation": regex_payload.get("explanation", ""),
    }
