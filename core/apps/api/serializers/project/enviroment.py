from rest_framework import serializers

from core.apps.api.models import EnviromentModel
from core.apps.api.serializers.fields import ProjectPkOrUuidField


class BaseEnviromentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnviromentModel
        fields = [
            "id",
            "key",
            "value",
        ]


class ListEnviromentSerializer(BaseEnviromentSerializer):
    class Meta(BaseEnviromentSerializer.Meta): ...


class RetrieveEnviromentSerializer(BaseEnviromentSerializer):
    class Meta(BaseEnviromentSerializer.Meta): ...


class CreateEnviromentSerializer(BaseEnviromentSerializer):
    project = ProjectPkOrUuidField()

    class Meta(BaseEnviromentSerializer.Meta):
        fields = [
            "id",
            "key",
            "value",
            "project",
        ]
        # Drop the auto-generated UniqueTogetherValidator on (key, project).
        # The view's perform_create() does update_or_create, so re-POSTing the
        # same key must upsert instead of failing with 400.
        validators = []
