from rest_framework import serializers

from core.apps.api.models import EnviromentModel
from core.apps.api.serializers.fields import ProjectPkOrUuidField

MASKED_VALUE = "••••"


class BaseEnviromentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnviromentModel
        fields = [
            "id",
            "key",
            "value",
            "secret",
        ]


class ListEnviromentSerializer(BaseEnviromentSerializer):
    value = serializers.SerializerMethodField()

    class Meta(BaseEnviromentSerializer.Meta):
        fields = [
            "id",
            "key",
            "value",
            "secret",
        ]

    def get_value(self, obj: EnviromentModel) -> str:
        if obj.secret:
            return MASKED_VALUE
        return obj.value


class RetrieveEnviromentSerializer(ListEnviromentSerializer):
    class Meta(ListEnviromentSerializer.Meta): ...


class CreateEnviromentSerializer(BaseEnviromentSerializer):
    project = ProjectPkOrUuidField()

    class Meta(BaseEnviromentSerializer.Meta):
        fields = [
            "id",
            "key",
            "value",
            "secret",
            "project",
        ]
        # Drop the auto-generated UniqueTogetherValidator on (key, project).
        # The view's perform_create() does update_or_create, so re-POSTing the
        # same key must upsert instead of failing with 400.
        validators = []
