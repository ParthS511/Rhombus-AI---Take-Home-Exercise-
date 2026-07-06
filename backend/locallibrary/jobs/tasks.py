from celery import shared_task

from . import data, orchestration


@shared_task
def ping():
    return "pong"


@shared_task(bind=True)
def process_regex_job(self, job_id):
    data.set_task_id(job_id, self.request.id)
    self.update_state(state="PROGRESS", meta={"progress": 5, "job_id": job_id})
    try:
        return orchestration.run_regex_job(job_id)
    except orchestration.RegexPatternError:
        raise
    except Exception as exc:
        if self.request.retries >= 3:
            raise
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task(bind=True)
def process_spark_regex_job(self, job_id):
    data.set_task_id(job_id, self.request.id)
    self.update_state(state="PROGRESS", meta={"progress": 5, "job_id": job_id})
    try:
        return orchestration.run_spark_regex_job(job_id)
    except orchestration.RegexPatternError:
        raise
    except Exception as exc:
        if self.request.retries >= 3:
            raise
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
