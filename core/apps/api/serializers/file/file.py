from rest_framework import serializers

from core.apps.api.models import FileModel
from core.apps.api.serializers.fields import ProjectPkOrUuidField


class BaseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileModel
        fields = [
            "file",
            "uuid",
            "filesize",
            "filetype",
            "project",
        ]


class ListFileSerializer(BaseFileSerializer):
    class Meta(BaseFileSerializer.Meta): ...


class RetrieveFileSerializer(BaseFileSerializer):
    class Meta(BaseFileSerializer.Meta): ...


class CreateFileSerializer(BaseFileSerializer):
    project = ProjectPkOrUuidField()

    class Meta(BaseFileSerializer.Meta):
        fields = [
            "file",
            "uuid",
            "filesize",
            "filetype",
            "project",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
            "filesize": {"read_only": True},
        }


class ModuleFileCreateSerializer(BaseFileSerializer):
    """project va user token orqali beriladi — input sifatida qabul qilinmaydi."""

    class Meta(BaseFileSerializer.Meta):
        fields = [
            "file",
            "uuid",
            "filesize",
            "filetype",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
            "filesize": {"read_only": True},
        }
