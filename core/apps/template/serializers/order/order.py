from rest_framework import serializers

from core.apps.template.models import TemplateOrderModel
from core.apps.template.serializers.template.template import RetrieveTemplateSerializer


class BaseTemplateOrderSerializer(serializers.ModelSerializer):
    template = RetrieveTemplateSerializer()

    class Meta:
        model = TemplateOrderModel
        fields = [
            "id",
            "template",
            "amount",
            "status",
            "payment_status",
            "created_at",
            "updated_at",
        ]


class ListTemplateOrderSerializer(BaseTemplateOrderSerializer):
    class Meta(BaseTemplateOrderSerializer.Meta): ...


class RetrieveTemplateOrderSerializer(BaseTemplateOrderSerializer):
    class Meta(BaseTemplateOrderSerializer.Meta): ...


class CreateTemplateOrderSerializer(BaseTemplateOrderSerializer):
    template = None

    class Meta(BaseTemplateOrderSerializer.Meta):
        fields = [
            "id",
            "template",
            "amount",
            "status",
            "payment_status",
        ]
        extra_kwargs = {
            "template": {
                "required": True,
            },
        }
        read_only_fields = ["amount", "status"]
