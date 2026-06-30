from django.urls import path
from . import views

urlpatterns = [
    path('regex/', views.regex_replace, name='regex-replace'),
]
