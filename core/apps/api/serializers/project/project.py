from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.serializers.project import ListBotSerializer


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
    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "flow"]


class CreateProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
        ]


class DebugProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "flow",
        ]
