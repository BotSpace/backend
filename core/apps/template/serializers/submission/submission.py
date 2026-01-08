from rest_framework import serializers
from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.serializers.template.category import ListTemplateCategorySerializer
from core.apps.template.serializers.template.feature import ListTemplateFeatureSerializer


class BaseTemplateSubmissionSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.apps.template.models.template import TemplateCategoryModel, TemplateFeatureModel
        self.fields['categories'] = serializers.PrimaryKeyRelatedField(
            queryset=TemplateCategoryModel.objects.all(),
            many=True,
            required=False,
            allow_empty=True,
            default=list
        )
        self.fields['features'] = serializers.PrimaryKeyRelatedField(
            queryset=TemplateFeatureModel.objects.all(),
            many=True,
            required=False,
            allow_empty=True,
            default=list
        )

    class Meta:
        model = TemplateSubmissionRequestModel
        fields = [
            "id",
            "user",
            "project",
            "name",
            "short_description",
            "description",
            "image",
            "video",
            "demo_url",
            "original_price",
            "categories",
            "features",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class CreateTemplateSubmissionSerializer(BaseTemplateSubmissionSerializer):
    """Serializer for creating template submission requests"""
    
    class Meta(BaseTemplateSubmissionSerializer.Meta):
        fields = [
            "id",
            "user",
            "project",
            "name",
            "short_description",
            "description",
            "image",
            "video",
            "demo_url",
            "original_price",
            "categories",
            "features",
        ]


class ListTemplateSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for listing template submission requests"""
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    categories = ListTemplateCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = TemplateSubmissionRequestModel
        fields = [
            "id",
            "user_phone",
            "project",
            "project_name",
            "name",
            "short_description",
            "image",
            "original_price",
            "categories",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RetrieveTemplateSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for retrieving template submission details"""
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    categories = ListTemplateCategorySerializer(many=True, read_only=True)
    features = ListTemplateFeatureSerializer(many=True, read_only=True)
    reviewed_by_phone = serializers.CharField(source="reviewed_by.phone", read_only=True, allow_null=True)
    
    class Meta:
        model = TemplateSubmissionRequestModel
        fields = [
            "id",
            "user_phone",
            "project",
            "project_name",
            "name",
            "short_description",
            "description",
            "image",
            "video",
            "demo_url",
            "original_price",
            "categories",
            "features",
            "status",
            "rejection_reason",
            "template",
            "reviewed_by_phone",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApproveTemplateSubmissionSerializer(serializers.Serializer):
    """Serializer for approving template submission"""
    discount = serializers.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        required=False, 
        default=0,
        help_text="Discount amount or percentage"
    )
    discount_type = serializers.ChoiceField(
        choices=["percent", "amount"],
        required=False,
        default="percent",
        help_text="Type of discount"
    )


class RejectTemplateSubmissionSerializer(serializers.Serializer):
    """Serializer for rejecting template submission"""
    rejection_reason = serializers.CharField(
        required=True,
        help_text="Reason for rejection"
    )
