from rest_framework import serializers

from core.apps.api.models import RelaseModel


class BaseRelaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelaseModel
        fields = [
            "id",
            "project",
            "flow",
            "version",
        ]


class ListRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta): ...


class RetrieveRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta): ...


class CreateRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta):
        fields = [
            "id",
            "project",
            "flow",
            "version",
        ]
