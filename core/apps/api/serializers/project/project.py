from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.serializers.project import ListBotSerializer


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
    class Meta(BaseProjectSerializer.Meta):...


class RetrieveProjectSerializer(BaseProjectSerializer):
    bot_for_debug = ListBotSerializer()
    bot_for_release = ListBotSerializer()

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "flow",
            "bot_for_debug",
            "bot_for_release"
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "bot_for_debug",
            "bot_for_release"
        ]