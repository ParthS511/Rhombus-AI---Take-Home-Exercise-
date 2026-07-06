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


class RegexGenerationSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class JobCreateSerializer(serializers.Serializer):
    ENGINE_CHOICES = ["python", "spark"]

    input_text = serializers.CharField(required=False, allow_blank=True, default="")
    pattern = serializers.CharField(required=False, allow_blank=True, default="")
    replacement = serializers.CharField(required=False, allow_blank=True, default="")
    natural_language_prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    engine = serializers.ChoiceField(
        choices=ENGINE_CHOICES,
        required=False,
        default="python",
        write_only=True,
    )

    def validate(self, attrs):
        if not attrs.get("input_text"):
            raise serializers.ValidationError({"input_text": "This field is required."})
        if not attrs.get("pattern") and not attrs.get("natural_language_prompt"):
            raise serializers.ValidationError(
                {"pattern": "Provide a regex pattern or a natural language prompt."}
            )
        return attrs


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
            "uploaded_file",
            "target_columns",
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
