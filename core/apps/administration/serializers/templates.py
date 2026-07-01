# type: ignore
from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.template.models import TemplateCategoryModel, TemplateFeatureModel, TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel


class AdminTemplateSerializer(serializers.ModelSerializer):
    """Read-only list/retrieve serializer for templates."""

    author_phone = serializers.CharField(source="author.phone", read_only=True)
    has_project = serializers.SerializerMethodField()

    def get_has_project(self, obj):
        return obj.project_id is not None

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
            "version",
            "author_id",
            "author_phone",
            "required_envs",
            "spec",
            "has_project",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminTemplateCreateSerializer(serializers.ModelSerializer):
    """Create a template FROM an existing project.

    Flow + spec are snapshotted server-side via build_spec_from_project;
    the client only supplies the project + presentation metadata.
    """

    project = serializers.PrimaryKeyRelatedField(queryset=ProjectModel.objects.all())
    categories = serializers.PrimaryKeyRelatedField(
        queryset=TemplateCategoryModel.objects.all(), many=True, required=False
    )
    features = serializers.PrimaryKeyRelatedField(
        queryset=TemplateFeatureModel.objects.all(), many=True, required=False
    )
    image = serializers.ImageField(required=False)
    # Admin may tweak the auto-built credentials/modules/envs and the
    # collections' default (seed) data before creating.
    # Shape: {"credentials": [...], "modules": [...], "envs": [...], "collections": [...]}.
    # Flow always comes from the project snapshot, never the client; collections
    # keep their project schema but their seed data may be overridden.
    spec_overrides = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = TemplateModel
        fields = (
            "id",
            "project",
            "name",
            "short_description",
            "description",
            "original_price",
            "discount",
            "discount_type",
            "demo_url",
            "categories",
            "features",
            "image",
            "is_verify",
            "spec_overrides",
        )


class AdminTemplateWriteSerializer(serializers.ModelSerializer):
    """Writable serializer used for PATCH /admin/templates/{id}/.

    Admin spec.credentials/modules/envs/collections ni tahrirlay oladi.
    """

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
            "version",
            "author_id",
            "author_phone",
            "required_envs",
            "spec",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "author_id",
            "author_phone",
            "views",
            "version",
            "created_at",
            "updated_at",
        )


class AdminTemplateSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for template submission list/retrieve/update.

    ``fields = "__all__"`` does NOT include serializer-level extra fields
    (SerializerMethodField, source-based CharField, etc.), so we enumerate
    every field explicitly to guarantee user_phone, project_name, template_name
    and *_detail fields appear in the output.
    """

    user_phone = serializers.CharField(source="user.phone", read_only=True)
    reviewed_by_phone = serializers.CharField(source="reviewed_by.phone", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    categories_detail = serializers.SerializerMethodField()
    features_detail = serializers.SerializerMethodField()

    class Meta:
        model = TemplateSubmissionRequestModel
        fields = (
            # --- identifiers / audit (read-only) ---
            "id",
            "user",
            "user_phone",
            "reviewed_by",
            "reviewed_by_phone",
            "reviewed_at",
            "created_at",
            "updated_at",
            # --- relations (read-only display names) ---
            "project",
            "project_name",
            "template",
            "template_name",
            # --- editable content ---
            "name",
            "short_description",
            "description",
            "image",
            "video",
            "demo_url",
            "original_price",
            "categories",
            "features",
            "required_envs",
            "status",
            "rejection_reason",
            # --- nested detail (read-only) ---
            "categories_detail",
            "features_detail",
        )
        read_only_fields = (
            "id",
            "user",
            "user_phone",
            "reviewed_by",
            "reviewed_by_phone",
            "reviewed_at",
            "project",
            "project_name",
            "template",
            "template_name",
            "categories_detail",
            "features_detail",
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
