import json
import re

from rest_framework import serializers

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.serializers.template.category import ListTemplateCategorySerializer
from core.apps.template.serializers.template.feature import ListTemplateFeatureSerializer
from core.apps.template.validators.template import validate_required_envs

_ENV_REF_RE = re.compile(r"\{\{\s*env\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_RESERVED_KEYS = {"RELEASE_BOT_TOKEN"}


def _extract_flow_env_keys(flow) -> set:
    """Return all {{env.KEY}} references found in the flow JSON (as a text dump)."""
    text = json.dumps(flow) if not isinstance(flow, str) else flow
    return {m.upper() for m in _ENV_REF_RE.findall(text)} - _RESERVED_KEYS


class RequiredEnvsField(serializers.Field):
    """Accepts list or JSON-encoded string, validates via shared validator."""

    def to_internal_value(self, data):
        return validate_required_envs(data)

    def to_representation(self, value):
        return value if isinstance(value, list) else []


class BaseTemplateSubmissionSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    required_envs = RequiredEnvsField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.apps.template.models.template import TemplateCategoryModel, TemplateFeatureModel

        self.fields["categories"] = serializers.PrimaryKeyRelatedField(
            queryset=TemplateCategoryModel.objects.all(),
            many=True,
            required=False,
            allow_empty=True,
            default=list,
        )
        self.fields["features"] = serializers.PrimaryKeyRelatedField(
            queryset=TemplateFeatureModel.objects.all(),
            many=True,
            required=False,
            allow_empty=True,
            default=list,
        )

    def _validate_flow_env_coverage(self, project, required_envs):
        """Check that every {{env.KEY}} reference in the project flow is declared in required_envs."""
        flow = getattr(project, "flow", None)
        if not flow:
            return
        declared_keys = {item["key"].upper() for item in required_envs}
        used_keys = _extract_flow_env_keys(flow)
        missing = used_keys - declared_keys
        if missing:
            sorted_missing = sorted(missing)
            raise serializers.ValidationError(
                {
                    "required_envs": [
                        f"Flow'da ishlatiladigan env'lar required_envs'da deklaratsiya qilinmagan: "
                        f"{', '.join(sorted_missing)}"
                    ]
                }
            )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Only run flow coverage check when required_envs is explicitly provided.
        # On PATCH without required_envs field, we skip (partial update doesn't re-validate
        # unchanged fields, so we can't enforce coverage without the current value).
        if "required_envs" in attrs:
            project = attrs.get("project") or getattr(self.instance, "project", None)
            required_envs = attrs["required_envs"]
            if project is not None:
                self._validate_flow_env_coverage(project, required_envs)
        return attrs

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
            "required_envs",
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
            "required_envs",
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
            "required_envs",
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
            "required_envs",
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
        help_text="Discount amount or percentage",
    )
    discount_type = serializers.ChoiceField(
        choices=["percent", "amount"],
        required=False,
        default="percent",
        help_text="Type of discount",
    )


class RejectTemplateSubmissionSerializer(serializers.Serializer):
    """Serializer for rejecting template submission"""

    rejection_reason = serializers.CharField(required=True, help_text="Reason for rejection")
