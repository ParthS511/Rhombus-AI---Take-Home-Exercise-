from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    input_text = models.TextField()
    natural_language_prompt = models.TextField(blank=True)
    pattern = models.TextField(blank=True)
    replacement = models.TextField(blank=True)
    task_id = models.CharField(max_length=255, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.pk} ({self.status})"


class Result(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="result")
    output_text = models.TextField(blank=True)
    matches = models.JSONField(default=list, blank=True)
    match_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Result for job {self.job_id}"
