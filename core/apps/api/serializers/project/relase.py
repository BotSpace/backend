from rest_framework import serializers

from core.apps.api.models import RelaseModel


class BaseRelaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelaseModel
        fields = [
            "id",
            "version",
            "status",
            "service_id",
        ]


class ListRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta): ...


class RetrieveRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta):
        fields = [
            "id",
            "project",
            "version",
            "status",
            "service_id",
            "flow",
        ]


class CreateRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta):
        fields = [
            "id",
            "project",
            "version",
        ]
        extra_kwargs = {"version": {"read_only": True}}
