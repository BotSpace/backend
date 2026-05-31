# type: ignore
from rest_framework import serializers

from core.apps.template.models import TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel


class AdminTemplateSerializer(serializers.ModelSerializer):
    author_phone = serializers.CharField(source="author.phone", read_only=True)

    class Meta:
        model = TemplateModel
        fields = (
            "id",
            "name",
            "slug",
            "image",
            "demo_url",
            "short_description",
            "description",
            "original_price",
            "discount",
            "discount_type",
            "is_verify",
            "views",
            "author_id",
            "author_phone",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminTemplateSubmissionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    reviewed_by_phone = serializers.CharField(
        source="reviewed_by.phone", read_only=True, default=None
    )
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    categories_detail = serializers.SerializerMethodField()
    features_detail = serializers.SerializerMethodField()

    class Meta:
        model = TemplateSubmissionRequestModel
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
            "user_phone",
            "created_at",
            "updated_at",
        )

    def get_categories_detail(self, obj):
        return [{"id": c.id, "name": c.name} for c in obj.categories.all()]

    def get_features_detail(self, obj):
        return [{"id": f.id, "name": f.name} for f in obj.features.all()]


class AdminVerifySerializer(serializers.Serializer):
    is_verify = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminSubmissionReviewSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
