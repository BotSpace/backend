from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer
from core.apps.api.serializers.project.relase import ListRelaseSerializer
from core.apps.api.services.dashboard import DashboardService
from core.apps.cms.services.mongo import get_project_collection
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
        """Get project plan info"""
        from core.apps.api.models import ProjectPlanModel

        try:
            project_plan = ProjectPlanModel.objects.select_related("plan").get(project=obj)
            return {
                "id": project_plan.plan.id,
                "name": project_plan.plan.get_name_display(),
                "status": project_plan.status,
                "current_users": project_plan.current_users,
                "max_users": project_plan.plan.max_users,
            }
        except ProjectPlanModel.DoesNotExist:
            return None

    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "release", "plan"]


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()
    debug_bot = serializers.SerializerMethodField()
    release_bot = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()

    def get_debug_bot(self, obj) -> bool:
        return True

    def get_release_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="RELEASE_BOT_TOKEN").exists()

    def get_plan(self, obj):
        """Get detailed project plan info"""
        from core.apps.api.models import ProjectPlanModel

        try:
            project_plan = ProjectPlanModel.objects.select_related("plan").get(project=obj)
            return {
                "id": project_plan.plan.id,
                "name": project_plan.plan.get_name_display(),
                "price": str(project_plan.plan.price),
                "status": project_plan.status,
                "current_users": project_plan.current_users,
                "max_users": project_plan.plan.max_users,
                "powered_by_botmother": project_plan.plan.powered_by_botmother,
                "limit_exceeded": project_plan.is_limit_exceeded(),
            }
        except ProjectPlanModel.DoesNotExist:
            return None

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "debug",
            "release",
            "debug_bot",
            "release_bot",
            "flow",
            "plan",
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer(required=False)
    release = None
    plan_id = serializers.IntegerField(required=False, write_only=True, help_text="Tarif ID (ixtiyoriy, default: FREE)")

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
            "plan_id",
        ]

    def validate_plan_id(self, value):
        """Validate plan exists and is active"""
        from core.apps.api.models import PlanModel

        try:
            plan = PlanModel.objects.get(id=value, is_active=True)
            return plan.id
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan")

    def create(self, validated_data):
        """Create project with plan assignment"""
        plan_id = validated_data.pop("plan_id", None)
        instance = super().create(validated_data)

        # If plan_id is specified, update the auto-created plan
        if plan_id:
            from core.apps.api.models import ProjectPlanModel, PlanModel
            from core.apps.api.enums.plan import PlanStatus

            try:
                project_plan = ProjectPlanModel.objects.get(project=instance)
                new_plan = PlanModel.objects.get(id=plan_id, is_active=True)
                project_plan.plan = new_plan
                project_plan.save()
            except (ProjectPlanModel.DoesNotExist, PlanModel.DoesNotExist):
                pass  # Fallback to signal-created FREE plan

        return instance


class CreateProjectFromTemplate(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(queryset=TemplateModel.objects.all())
    name = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255)
