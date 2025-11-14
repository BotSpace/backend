from rest_framework import serializers

from core.apps.template.models import TemplateModel


class BaseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateModel
        fields = [
            "id",
            "name",
        ]


class ListTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta): ...


class RetrieveTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta): ...


class CreateTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
