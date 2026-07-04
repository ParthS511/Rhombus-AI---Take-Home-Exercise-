from rest_framework import serializers

from jobs.models import Job, Result


class RegexReplacementSerializer(serializers.Serializer):
    text = serializers.CharField()
    pattern = serializers.CharField()
    replacement = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_pattern(self, value):
        if value == "":
            raise serializers.ValidationError("Pattern must be a non-empty string.")
        return value


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = [
            "id",
            "job",
            "output_text",
            "matches",
            "match_count",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobSerializer(serializers.ModelSerializer):
    result = ResultSerializer(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "status",
            "progress",
            "input_text",
            "natural_language_prompt",
            "pattern",
            "replacement",
            "task_id",
            "error_message",
            "result",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "progress",
            "task_id",
            "error_message",
            "result",
            "created_at",
            "updated_at",
        ]
