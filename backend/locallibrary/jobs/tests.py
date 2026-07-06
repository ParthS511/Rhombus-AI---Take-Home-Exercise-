import json
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from .orchestration import (
    RegexPatternError,
    _apply_spark_regex_to_file,
    run_regex_job,
    run_spark_regex_job,
)
from .models import Job, Result


class JobResultModelTests(TestCase):
    def test_job_defaults_to_pending_with_zero_progress(self):
        job = Job.objects.create(input_text="Order 123")

        self.assertEqual(job.status, Job.Status.PENDING)
        self.assertEqual(job.progress, 0)
        self.assertEqual(str(job), f"Job {job.pk} (pending)")

    def test_result_belongs_to_job(self):
        job = Job.objects.create(
            input_text="Order 123",
            pattern=r"\d+",
            replacement="#",
        )
        result = Result.objects.create(
            job=job,
            output_text="Order #",
            matches=[{"match": "123", "start": 6, "end": 9}],
            match_count=1,
            metadata={"engine": "spark-local"},
        )

        self.assertEqual(job.result, result)
        self.assertEqual(result.match_count, 1)
        self.assertEqual(result.metadata["engine"], "spark-local")

    def test_job_progress_must_be_between_zero_and_one_hundred(self):
        job = Job(input_text="Order 123", progress=101)

        with self.assertRaises(ValidationError):
            job.full_clean()


class RegexJobOrchestrationTests(TestCase):
    def test_run_regex_job_marks_job_succeeded_and_saves_result(self):
        job = Job.objects.create(
            input_text="Order 123 and order 456",
            pattern=r"\d+",
            replacement="#",
        )

        payload = run_regex_job(job.id)
        job.refresh_from_db()

        self.assertEqual(job.status, Job.Status.SUCCEEDED)
        self.assertEqual(job.progress, 100)
        self.assertEqual(payload["result"], "Order # and order #")
        self.assertEqual(job.result.output_text, "Order # and order #")
        self.assertEqual(job.result.match_count, 2)
        self.assertEqual(job.result.metadata["engine"], "python-re")

    def test_run_regex_job_marks_job_failed_for_invalid_pattern(self):
        job = Job.objects.create(input_text="abc", pattern="[", replacement="x")

        with self.assertRaises(RegexPatternError):
            run_regex_job(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.FAILED)
        self.assertIn("Invalid regex pattern", job.error_message)

    @patch("jobs.orchestration.generate_regex_from_prompt")
    def test_run_regex_job_generates_pattern_from_prompt_in_worker(self, mock_generate):
        mock_generate.return_value = {
            "pattern": r"\d+",
            "replacement": "#",
            "explanation": "Match digit runs.",
            "source": "fallback",
        }
        job = Job.objects.create(
            input_text="Order 123",
            natural_language_prompt="replace numbers",
        )

        payload = run_regex_job(job.id)
        job.refresh_from_db()

        mock_generate.assert_called_once_with("replace numbers")
        self.assertEqual(job.status, Job.Status.SUCCEEDED)
        self.assertEqual(job.pattern, r"\d+")
        self.assertEqual(job.replacement, "#")
        self.assertEqual(payload["result"], "Order #")
        self.assertEqual(job.result.metadata["regex_source"], "fallback")

    @patch("jobs.orchestration._apply_spark_regex")
    def test_run_spark_regex_job_marks_job_succeeded_and_saves_result(self, mock_spark):
        mock_spark.return_value = "Order #"
        job = Job.objects.create(
            input_text="Order 123",
            pattern=r"\d+",
            replacement="#",
        )

        payload = run_spark_regex_job(job.id)
        job.refresh_from_db()

        mock_spark.assert_called_once_with(
            text="Order 123",
            pattern=r"\d+",
            replacement="#",
        )
        self.assertEqual(job.status, Job.Status.SUCCEEDED)
        self.assertEqual(payload["result"], "Order #")
        self.assertEqual(job.result.output_text, "Order #")
        self.assertEqual(job.result.metadata["engine"], "spark-local")

    def test_spark_file_processing_falls_back_when_pandas_is_unavailable(self):
        class FakeJob:
            def __init__(self):
                self.id = 42
                self.status = "pending"
                self.progress = 0
                self.error_message = ""

            def save(self, update_fields=None):
                return None

        class FakeDataFrame:
            def __init__(self, rows, columns):
                self._rows = rows
                self.columns = columns
                self.schema = SimpleNamespace(fields=[SimpleNamespace(name="name", dataType="StringType")])
                self.write = SimpleNamespace(mode=lambda *args, **kwargs: SimpleNamespace(parquet=lambda *args, **kwargs: None))

            def withColumn(self, name, expr):
                return self

            def limit(self, count):
                return self

            def toPandas(self):
                raise ModuleNotFoundError("No module named 'pandas'")

            def collect(self):
                return self._rows

            def count(self):
                return len(self._rows)

        class FakeBuilder:
            def appName(self, *args, **kwargs):
                return self

            def master(self, *args, **kwargs):
                return self

            def config(self, *args, **kwargs):
                return self

            def getOrCreate(self):
                return FakeSparkSession()

        class FakeReader:
            def option(self, *args, **kwargs):
                return self

            def csv(self, path):
                return FakeDataFrame([{"name": "Ada"}], ["name"])

        class FakeSparkSession:
            builder = FakeBuilder()

            def __init__(self):
                self.read = FakeReader()

            def stop(self):
                return None

        fake_sql_module = SimpleNamespace(SparkSession=FakeSparkSession)
        fake_functions_module = SimpleNamespace(
            col=lambda name: name,
            regexp_replace=lambda value, pattern, replacement: value,
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as source_file:
            with patch.dict(
                sys.modules,
                {
                    "pyspark.sql": fake_sql_module,
                    "pyspark.sql.functions": fake_functions_module,
                },
            ):
                output_path, sample_csv, rows_count, columns = _apply_spark_regex_to_file(
                    file_path=source_file.name,
                    pattern=r"\d+",
                    replacement="#",
                    target_columns="name",
                    job=FakeJob(),
                )

        self.assertIn("job_42", output_path)
        self.assertTrue(sample_csv.startswith("name"))
        self.assertIn("Ada", sample_csv)
        self.assertEqual(rows_count, 1)
        self.assertEqual(columns, ["name"])

    def test_spark_file_processing_rejects_missing_target_columns(self):
        class FakeDataFrame:
            columns = ["name"]
            schema = SimpleNamespace(fields=[SimpleNamespace(name="name", dataType="StringType")])

        class FakeBuilder:
            def appName(self, *args, **kwargs):
                return self

            def master(self, *args, **kwargs):
                return self

            def getOrCreate(self):
                return FakeSparkSession()

        class FakeReader:
            def option(self, *args, **kwargs):
                return self

            def csv(self, path):
                return FakeDataFrame()

        class FakeSparkSession:
            builder = FakeBuilder()

            def __init__(self):
                self.read = FakeReader()

            def stop(self):
                return None

        fake_sql_module = SimpleNamespace(SparkSession=FakeSparkSession)
        fake_functions_module = SimpleNamespace(
            col=lambda name: name,
            regexp_replace=lambda value, pattern, replacement: value,
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as source_file:
            with patch.dict(
                sys.modules,
                {
                    "pyspark.sql": fake_sql_module,
                    "pyspark.sql.functions": fake_functions_module,
                },
            ):
                with self.assertRaisesMessage(ValueError, "Target columns not found"):
                    _apply_spark_regex_to_file(
                        file_path=source_file.name,
                        pattern=r"\d+",
                        replacement="#",
                        target_columns="missing",
                    )


class RegexReplaceTests(TestCase):
    def post_regex(self, payload):
        return self.client.post(
            reverse("regex-replace"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_returns_matches_and_replaced_text(self):
        response = self.post_regex(
            {
                "text": "Order 123 and order 456",
                "pattern": r"\d+",
                "replacement": "#",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "matches": [
                    {"match": "123", "start": 6, "end": 9, "groups": []},
                    {"match": "456", "start": 20, "end": 23, "groups": []},
                ],
                "match_count": 2,
                "result": "Order # and order #",
            },
        )

    def test_returns_empty_matches_when_pattern_is_not_found(self):
        response = self.post_regex(
            {
                "text": "No digits here",
                "pattern": r"\d+",
                "replacement": "#",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matches"], [])
        self.assertEqual(response.json()["match_count"], 0)
        self.assertEqual(response.json()["result"], "No digits here")

    def test_rejects_invalid_regex_pattern(self):
        response = self.post_regex(
            {
                "text": "abc",
                "pattern": "[",
                "replacement": "x",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid regex pattern", response.json()["error"])

    def test_requires_text_and_pattern(self):
        response = self.post_regex({"replacement": "x"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json()["error"])


class JobCreateApiTests(TestCase):
    @patch("jobs.api.views.process_regex_job.delay")
    def test_create_job_persists_job_and_dispatches_task(self, mock_delay):
        mock_delay.return_value.id = "celery-task-123"

        response = self.client.post(
            reverse("job-create"),
            data=json.dumps(
                {
                    "input_text": "Order 123",
                    "pattern": r"\d+",
                    "replacement": "#",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        job = Job.objects.get()
        mock_delay.assert_called_once_with(job.id)
        self.assertEqual(job.status, Job.Status.PENDING)
        self.assertEqual(job.task_id, "celery-task-123")
        self.assertEqual(response.json()["id"], job.id)
        self.assertEqual(response.json()["task_id"], "celery-task-123")

    @patch("jobs.api.views.process_spark_regex_job.delay")
    def test_create_job_can_dispatch_spark_task(self, mock_delay):
        mock_delay.return_value.id = "spark-task-123"

        response = self.client.post(
            reverse("job-create"),
            data=json.dumps(
                {
                    "input_text": "Order 123",
                    "pattern": r"\d+",
                    "replacement": "#",
                    "engine": "spark",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        job = Job.objects.get()
        mock_delay.assert_called_once_with(job.id)
        self.assertEqual(job.task_id, "spark-task-123")

    @patch("jobs.api.views.process_regex_job.delay")
    def test_create_job_with_prompt_returns_immediately_without_generating_pattern(self, mock_delay):
        mock_delay.return_value.id = "celery-task-123"

        response = self.client.post(
            reverse("job-create"),
            data=json.dumps(
                {
                    "input_text": "Order 123",
                    "natural_language_prompt": "replace numbers",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        job = Job.objects.get()
        self.assertEqual(job.pattern, "")
        self.assertEqual(job.replacement, "")
        mock_delay.assert_called_once_with(job.id)

    @patch("jobs.api.views.process_regex_job.delay")
    def test_create_job_rejects_invalid_payload_before_dispatch(self, mock_delay):
        response = self.client.post(
            reverse("job-create"),
            data=json.dumps({"replacement": "#"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Job.objects.count(), 0)
        mock_delay.assert_not_called()

    @patch("jobs.api.views.process_spark_regex_job.delay")
    def test_create_job_accepts_file_upload_and_dispatches_spark_task(self, mock_delay):
        mock_delay.return_value.id = "spark-task-123"

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                upload = SimpleUploadedFile(
                    "orders.csv",
                    b"name,order\nAda,Order 123\n",
                    content_type="text/csv",
                )
                response = self.client.post(
                    reverse("job-create"),
                    data={
                        "file": upload,
                        "pattern": r"\d+",
                        "replacement": "#",
                        "target_columns": "order",
                    },
                )

                self.assertEqual(response.status_code, 202)
                job = Job.objects.get()
                self.assertTrue(os.path.exists(job.uploaded_file))
                self.assertEqual(job.target_columns, "order")
                self.assertIn("Order 123", job.input_text)
        mock_delay.assert_called_once_with(job.id)

    @patch("jobs.api.views.process_spark_regex_job.delay")
    def test_create_job_rejects_file_upload_without_pattern_or_prompt(self, mock_delay):
        upload = SimpleUploadedFile("orders.csv", b"name\nAda\n", content_type="text/csv")

        response = self.client.post(reverse("job-create"), data={"file": upload})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Job.objects.count(), 0)
        mock_delay.assert_not_called()


class JobResultApiTests(TestCase):
    def test_job_result_returns_paginated_csv_rows(self):
        job = Job.objects.create(input_text="sample", pattern=r"\d+")
        Result.objects.create(
            job=job,
            output_text="name,order\nAda,Order #\nGrace,Order #\n",
            matches=[],
            metadata={"engine": "spark-file"},
        )

        response = self.client.get(reverse("job-result", args=[job.id]), {"page_size": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [{"name": "Ada", "order": "Order #"}],
                "columns": ["name", "order"],
                "total_pages": 2,
                "page": 1,
            },
        )


class TaskPingApiTests(TestCase):
    @patch("jobs.api.views.ping.delay")
    def test_ping_task_runs_through_celery_and_returns_result(self, mock_delay):
        mock_result = mock_delay.return_value
        mock_result.id = "ping-task-123"
        mock_result.get.return_value = "pong"

        response = self.client.post(reverse("task-ping"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"task_id": "ping-task-123", "result": "pong"},
        )
        mock_result.get.assert_called_once_with(timeout=10)


class LlmRegexApiTests(TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    def test_generate_regex_returns_forced_json_shape_without_api_key(self):
        response = self.client.post(
            reverse("llm-regex"),
            data=json.dumps({"prompt": "replace email addresses"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload.keys()),
            {"pattern", "replacement", "explanation", "source"},
        )
        self.assertEqual(payload["source"], "fallback")
        self.assertIn("EMAIL", payload["replacement"])

    def test_generate_regex_can_use_groq_openai_compatible_client(self):
        class FakeCompletions:
            def create(self, **kwargs):
                FakeOpenAI.create_kwargs = kwargs
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content=json.dumps(
                                    {
                                        "pattern": r"\d+",
                                        "replacement": "#",
                                        "explanation": "Match digit runs.",
                                    }
                                )
                            )
                        )
                    ]
                )

        class FakeOpenAI:
            init_kwargs = None
            create_kwargs = None

            def __init__(self, **kwargs):
                FakeOpenAI.init_kwargs = kwargs
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "test-groq-key",
                "GROQ_MODEL": "test-groq-model",
            },
        ):
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}):
                response = self.client.post(
                    reverse("llm-regex"),
                    data=json.dumps({"prompt": "replace numbers"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "groq")
        self.assertEqual(FakeOpenAI.init_kwargs["api_key"], "test-groq-key")
        self.assertEqual(FakeOpenAI.init_kwargs["base_url"], "https://api.groq.com/openai/v1")
        self.assertEqual(FakeOpenAI.create_kwargs["model"], "test-groq-model")
