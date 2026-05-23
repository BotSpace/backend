from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample
from core.apps.api.models import PlanModel

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import EnviromentModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer
from core.apps.api.serializers.project.relase import ListRelaseSerializer
from core.apps.api.services.dashboard import DashboardService
from core.apps.cms_legacy.services.mongo import get_project_collection
from core.apps.template.models import TemplateModel


class BaseProjectSerializer(serializers.ModelSerializer):
    release = ListRelaseSerializer()
    users = serializers.SerializerMethodField()

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(instance=instance, *args, **kwargs)
        self.dashboardService = DashboardService()

    def to_representation(self, instance):
        self.dashboardService.set_collection(get_project_collection(instance))
        return super().to_representation(instance)

    def get_users(self, obj) -> int:
        return self.dashboardService.users_count()

    def validate_plan_id(self, value):
        """Validate plan exists and is active"""
        try:
            plan = PlanModel.objects.get(id=value, is_active=True)
            return plan.pk
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan")

    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "name",
            "users",
            "username",
            "avatar",
        ]


class ListProjectSerializer(BaseProjectSerializer):
    plan = serializers.SerializerMethodField()

    def get_plan(self, obj):
        """Get project plan info (relies on prefetched plan_subscription__plan)."""
        project_plan = getattr(obj, "plan_subscription", None)
        if project_plan is None:
            return None
        plan = project_plan.plan
        return {
            "id": plan.id,
            "name": plan.get_name_display(),
            "status": project_plan.status,
            "current_users": project_plan.current_users,
            "max_users": plan.max_users,
        }

    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "release", "plan"]


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()
    debug_bot = serializers.SerializerMethodField()
    release_bot = serializers.SerializerMethodField()
    debug_uuid = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()

    def get_debug_uuid(self, obj) -> str:
        return obj.debug_webhook_uuid

    def get_debug_bot(self, obj) -> bool:
        return True

    def get_release_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="RELEASE_BOT_TOKEN").exists()

    def get_plan(self, obj):
        """Get detailed project plan info (relies on prefetched plan_subscription__plan)."""
        project_plan = getattr(obj, "plan_subscription", None)
        if project_plan is None:
            return None
        plan = project_plan.plan
        return {
            "id": plan.id,
            "name": plan.get_name_display(),
            "price": str(plan.price),
            "status": project_plan.status,
            "current_users": project_plan.current_users,
            "max_users": plan.max_users,
            "powered_by_botmother": plan.powered_by_botmother,
            "limit_exceeded": project_plan.is_limit_exceeded(),
        }

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "debug",
            "release",
            "debug_bot",
            "release_bot",
            "debug_uuid",
            "flow",
            "plan",
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer(required=False)
    release = None

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
        ]
        examples = [
            OpenApiExample(
                "Loyiha yaratish",
                value={
                    "name": "Mening botim",
                    "flow": {},
                    "debug": {"token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"},
                },
                description="Loyiha yaratish (bepul, limitsiz)",
            )
        ]


class CreateProjectFromTemplate(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(queryset=TemplateModel.objects.all(), help_text="Shablon ID")
    name = serializers.CharField(max_length=255, help_text="Loyiha nomi")
    token = serializers.CharField(max_length=255, help_text="Release bot tokeni")

    class Meta:
        examples = [
            OpenApiExample(
                "Shablondan loyiha yaratish",
                value={
                    "template": 1,
                    "name": "Mening shablon loyiham",
                    "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                },
                description="Sotib olingan shablondan loyiha yaratish",
            )
        ]
