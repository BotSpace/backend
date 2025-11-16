from rest_framework import serializers

from core.apps.template.models import TemplateModel
from core.apps.template.serializers.template.category import ListTemplateCategorySerializer
from core.apps.template.serializers.template.feature import ListTemplateFeatureSerializer, MiniTemplateFeatureSerializer


class BaseTemplateSerializer(serializers.ModelSerializer):
    features = MiniTemplateFeatureSerializer(many=True)
    categories = ListTemplateCategorySerializer(many=True)
    likes = serializers.SerializerMethodField()

    def get_likes(self, obj) -> int:
        return obj.likes.count()

    class Meta:
        model = TemplateModel
        fields = [
            "id",
            "name",
            "image",
            "price",
            "views",
            "likes",
            "original_price",
            "discount",
            "discount_type",
            "categories",
            "features",
        ]


class ListTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta): ...


class RetrieveTemplateSerializer(BaseTemplateSerializer):
    features = ListTemplateFeatureSerializer(many=True)

    class Meta(BaseTemplateSerializer.Meta):
        fields = [
            "id",
            "name",
            "image",
            "video",
            "short_description",
            "description",
            "price",
            "views",
            "likes",
            "original_price",
            "discount",
            "discount_type",
            "categories",
            "features",
        ]


class CreateTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
