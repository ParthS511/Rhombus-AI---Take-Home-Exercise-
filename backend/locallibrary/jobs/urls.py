from django.urls import path

from .api import views

urlpatterns = [
    path('regex/', views.regex_replace, name='regex-replace'),
]
