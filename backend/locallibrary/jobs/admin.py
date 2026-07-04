from django.contrib import admin

from .models import Job, Result


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "progress", "task_id", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("id", "task_id", "pattern", "natural_language_prompt")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "match_count", "created_at", "updated_at")
    search_fields = ("job__id",)
    readonly_fields = ("created_at", "updated_at")
