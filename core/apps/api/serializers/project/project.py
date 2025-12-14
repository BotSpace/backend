from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample
from core.apps.api.enums.plan import PlanType
from core.apps.api.models import PlanModel

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import EnviromentModel
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
    debug_uuid = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()

    def get_debug_uuid(self, obj) -> str:
        return obj.debug_webhook_uuid

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
            "debug_uuid",
            "flow",
            "plan",
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer(required=False)
    release = None
    plan_id = serializers.IntegerField(
        required=True, write_only=True, help_text="Tarif ID (majburiy). Balansingiz yetarli bo'lishi kerak."
    )

    def validate(self, attrs):
        plan_id = attrs.get("plan_id")
        try:
            plan = PlanModel.objects.get(id=plan_id, is_active=True)
            user = self.context["request"].user
            if plan.name == PlanType.FREE.value:
                project = ProjectModel.objects.filter(
                    owner=user, plan_subscription__plan__name=PlanType.FREE.value
                ).first()
                if project is not None:
                    raise serializers.ValidationError(
                        detail={"plan_id": "Kechirasiz bepul tarifda faqat bitta loyiha yaratish mumkun"}
                    )

            if user.balance < plan.price:
                raise serializers.ValidationError(
                    {"plan_id": "Balansingiz yetarli emas. Kerakli: {}, Mavjud: {}".format(plan.price, user.balance)}
                )
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError({"plan_id": "Noto'g'ri yoki nofaol tarif"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("plan_id", None)
        return super().create(validated_data)

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
            "plan_id",
        ]
        examples = [
            OpenApiExample(
                "Loyiha yaratish",
                value={
                    "name": "Mening botim",
                    "plan_id": 1,
                    "flow": {},
                    "debug": {"token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"},
                },
                description="FREE yoki boshqa tarifda loyiha yaratish",
            )
        ]


class CreateProjectFromTemplate(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(queryset=TemplateModel.objects.all(), help_text="Shablon ID")
    name = serializers.CharField(max_length=255, help_text="Loyiha nomi")
    token = serializers.CharField(max_length=255, help_text="Release bot tokeni")
    plan_id = serializers.IntegerField(
        required=True, write_only=True, help_text="Tarif ID (majburiy). Balansingiz yetarli bo'lishi kerak."
    )

    def validate(self, attrs):
        plan_id = attrs.get("plan_id")
        if plan_id:
            try:
                plan = PlanModel.objects.get(id=plan_id, is_active=True)
                user = self.context["request"].user
                if user.balance < plan.price:
                    raise serializers.ValidationError(
                        {
                            "plan_id": "Balansingiz yetarli emas. Kerakli: {}, Mavjud: {}".format(
                                plan.price, user.balance
                            )
                        }
                    )
            except PlanModel.DoesNotExist:
                raise serializers.ValidationError({"plan_id": "Noto'g'ri yoki nofaol tarif"})
        return attrs

    class Meta:
        examples = [
            OpenApiExample(
                "Shablondan loyiha yaratish",
                value={
                    "template": 1,
                    "name": "Mening shablon loyiham",
                    "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                    "plan_id": 1,
                },
                description="Sotib olingan shablondan loyiha yaratish",
            )
        ]
