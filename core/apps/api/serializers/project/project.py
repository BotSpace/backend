from typing import List
from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer
from core.apps.api.serializers.project.relase import ListRelaseSerializer


class BaseProjectSerializer(serializers.ModelSerializer):
    release = ListRelaseSerializer()
    users = serializers.SerializerMethodField()

    def get_users(self, obj) -> int:
        return 0

    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "name",
        ]


class ListProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "release"]


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()
    debug_bot = serializers.SerializerMethodField()
    release_bot = serializers.SerializerMethodField()

    def get_debug_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="BOT_TOKEN").exists()

    def get_release_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="RELEASE_BOT_TOKEN").exists()

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "debug",
            "release",
            "debug_bot",
            "release_bot",
            "flow",
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer(required=False)
    release = None

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
