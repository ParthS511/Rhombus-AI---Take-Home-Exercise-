from django.urls import path

from .api import views

urlpatterns = [
    path('jobs/', views.create_job, name='job-create'),
    path('regex/', views.regex_replace, name='regex-replace'),
]
