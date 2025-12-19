from rest_framework import serializers

from core.apps.template.models import TemplateCategoryModel


class BaseTemplateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateCategoryModel
        fields = [
            "id",
            "name",
        ]


class ListTemplateCategorySerializer(BaseTemplateCategorySerializer):
    class Meta(BaseTemplateCategorySerializer.Meta): ...


class RetrieveTemplateCategorySerializer(BaseTemplateCategorySerializer):
    class Meta(BaseTemplateCategorySerializer.Meta):
        fields = [
            "id",
            "name",
        ]


class CreateTemplateCategorySerializer(BaseTemplateCategorySerializer):
    class Meta(BaseTemplateCategorySerializer.Meta):
        fields = [
            "id",
            "name",
        ]
