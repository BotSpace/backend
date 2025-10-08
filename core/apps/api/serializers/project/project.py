from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import DebugModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer


class BaseProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "name",
        ]


class ListProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta): ...


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()

    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "debug", "flow"]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer()

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
        ]

    def create(self, validated_data: dict):
        if "debug" in validated_data:
            debug = validated_data.pop("debug")
        else:
            debug = {}
        instance = super().create(validated_data)
        DebugModel.objects.create(project=instance, **debug)
        return instance
