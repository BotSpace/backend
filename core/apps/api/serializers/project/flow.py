from rest_framework import serializers

from core.apps.api.models import FlowModel


class BaseFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowModel
        fields = [
            "id",
            "flow",
        ]


class ListFlowSerializer(BaseFlowSerializer):
    class Meta(BaseFlowSerializer.Meta): ...


class RetrieveFlowSerializer(BaseFlowSerializer):
    class Meta(BaseFlowSerializer.Meta): ...


class CreateFlowSerializer(BaseFlowSerializer):
    class Meta(BaseFlowSerializer.Meta):
        fields = [
            "id",
        ]
