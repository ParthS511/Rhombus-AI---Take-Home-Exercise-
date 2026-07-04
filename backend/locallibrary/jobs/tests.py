import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .orchestration import RegexPatternError, run_regex_job
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
