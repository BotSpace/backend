from rest_framework import serializers

from core.apps.api.models import DebugModel


class BaseDebugSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebugModel
        fields = [
            "id",
            "status",
            "service_id",
            # "flow_hash",
        ]


class ListDebugSerializer(BaseDebugSerializer):
    class Meta(BaseDebugSerializer.Meta): ...


class RetrieveDebugSerializer(BaseDebugSerializer):
    class Meta(BaseDebugSerializer.Meta):
        fields = [*BaseDebugSerializer.Meta.fields, "flow"]


class CreateDebugSerializer(BaseDebugSerializer):
    class Meta(BaseDebugSerializer.Meta):
        fields = [
            "flow",
        ]
        extra_kwargs = {"flow": {"required": True}}
