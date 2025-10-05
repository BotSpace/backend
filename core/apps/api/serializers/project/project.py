from rest_framework import serializers

from core.apps.api.models import ProjectModel


class BaseProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "name",
            "bot_is_released",
            "bot_is_debug",
        ]


class ListProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta): ...


class RetrieveProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta): ...


class CreateProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
