from rest_framework import serializers

from core.apps.template.models import TemplateFeatureModel


class BaseTemplateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateFeatureModel
        fields = [
            "id",
            "name",
            "value",
        ]


class ListTemplateFeatureSerializer(BaseTemplateFeatureSerializer):
    class Meta(BaseTemplateFeatureSerializer.Meta): ...


class RetrieveTemplateFeatureSerializer(BaseTemplateFeatureSerializer):
    class Meta(BaseTemplateFeatureSerializer.Meta):
        fields = [
            "id",
            "name",
            "value",
        ]


class CreateTemplateFeatureSerializer(BaseTemplateFeatureSerializer):
    class Meta(BaseTemplateFeatureSerializer.Meta):
        fields = [
            "id",
            "name",
            "value",
        ]


class MiniTemplateFeatureSerializer(BaseTemplateFeatureSerializer):
    class Meta(BaseTemplateFeatureSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
