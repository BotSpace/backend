# type: ignore
from rest_framework import serializers

from core.apps.template.enums.order import TemplateOrderStatusEnum
from core.apps.template.models import TemplateModel
from core.apps.template.models.order import TemplateOrderModel
from core.apps.template.serializers.template.category import ListTemplateCategorySerializer
from core.apps.template.serializers.template.feature import ListTemplateFeatureSerializer, MiniTemplateFeatureSerializer


class BaseTemplateSerializer(serializers.ModelSerializer):
    features = MiniTemplateFeatureSerializer(many=True)
    categories = ListTemplateCategorySerializer(many=True)
    likes = serializers.SerializerMethodField()
    is_order = serializers.SerializerMethodField()

    def get_is_order(self, obj) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        user = request.user
        if not user.is_authenticated:
            return False
        if TemplateOrderModel.objects.filter(
            user=user, template=obj, payment_status=True, status=TemplateOrderStatusEnum.CONFIRM.value
        ).exists():
            return True
        return False

    def get_likes(self, obj) -> int:
        return obj.likes.count()

    class Meta:
        model = TemplateModel
        fields = [
            "id",
            "name",
            "slug",
            "image",
            "price",
            "views",
            "likes",
            "original_price",
            "discount",
            "discount_type",
            "categories",
            "features",
            "is_order",
        ]


class ListTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta): ...


class RetrieveTemplateSerializer(BaseTemplateSerializer):
    features = ListTemplateFeatureSerializer(many=True)

    class Meta(BaseTemplateSerializer.Meta):
        fields = [
            "id",
            "name",
            "slug",
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
            "is_order",
        ]


class CreateTemplateSerializer(BaseTemplateSerializer):
    class Meta(BaseTemplateSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
