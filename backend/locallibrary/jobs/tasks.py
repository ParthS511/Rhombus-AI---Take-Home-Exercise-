from celery import shared_task

from . import data, orchestration


@shared_task
def ping():
    return "pong"


@shared_task(bind=True)
def process_regex_job(self, job_id):
    data.set_task_id(job_id, self.request.id)
    return orchestration.run_regex_job(job_id)
