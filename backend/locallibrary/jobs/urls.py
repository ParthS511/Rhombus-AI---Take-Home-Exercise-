from django.urls import path

from .api import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('jobs/', views.create_job, name='job-create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job-detail'),
    path('jobs/<int:job_id>/result/', views.job_result, name='job-result'),
    path('llm/regex/', views.generate_regex, name='llm-regex'),
    path('regex/', views.regex_replace, name='regex-replace'),
    path('tasks/ping/', views.ping_task, name='task-ping'),
]
