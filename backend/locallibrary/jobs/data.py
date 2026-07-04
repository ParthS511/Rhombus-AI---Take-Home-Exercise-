from .models import Job, Result


def create_job(
    *,
    input_text,
    pattern="",
    replacement="",
    natural_language_prompt="",
):
    return Job.objects.create(
        input_text=input_text,
        pattern=pattern,
        replacement=replacement,
        natural_language_prompt=natural_language_prompt,
    )


def get_job(job_id):
    return Job.objects.get(id=job_id)


def set_task_id(job_id, task_id):
    Job.objects.filter(id=job_id).update(task_id=task_id)


def mark_running(job, *, progress=10):
    job.status = Job.Status.RUNNING
    job.progress = progress
    job.error_message = ""
    job.save(update_fields=["status", "progress", "error_message", "updated_at"])
    return job


def mark_succeeded(job):
    job.status = Job.Status.SUCCEEDED
    job.progress = 100
    job.error_message = ""
    job.save(update_fields=["status", "progress", "error_message", "updated_at"])
    return job


def mark_failed(job, error_message):
    job.status = Job.Status.FAILED
    job.error_message = str(error_message)
    job.save(update_fields=["status", "error_message", "updated_at"])
    return job


def save_result(*, job, output_text, matches, metadata=None):
    result, _ = Result.objects.update_or_create(
        job=job,
        defaults={
            "output_text": output_text,
            "matches": matches,
            "match_count": len(matches),
            "metadata": metadata or {},
        },
    )
    return result
