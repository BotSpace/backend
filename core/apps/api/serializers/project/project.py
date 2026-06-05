from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample
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

    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "uuid",
            "name",
            "users",
            "username",
            "avatar",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
        }


class ListProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "release"]


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()
    debug_bot = serializers.SerializerMethodField()
    release_bot = serializers.SerializerMethodField()
    debug_uuid = serializers.SerializerMethodField()

    def get_debug_uuid(self, obj) -> str:
        return obj.debug_webhook_uuid

    def get_debug_bot(self, obj) -> bool:
        return True

    def get_release_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="RELEASE_BOT_TOKEN").exists()

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "debug",
            "release",
            "debug_bot",
            "release_bot",
            "debug_uuid",
            "flow",
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
    envs = serializers.DictField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=dict,
        help_text="Template'ning required_envs kalitlari uchun qiymatlar: {KEY: value}",
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        template = attrs.get("template")
        envs = attrs.get("envs", {})
        required_envs = getattr(template, "required_envs", []) or []
        missing = []
        for item in required_envs:
            key = item.get("key", "")
            if not key:
                continue
            if not envs.get(key, "").strip():
                missing.append(key)
        if missing:
            raise serializers.ValidationError(
                {"envs": [f"{key} majburiy" for key in missing]}
            )
        return attrs

    class Meta:
        examples = [
            OpenApiExample(
                "Shablondan loyiha yaratish",
                value={
                    "template": 1,
                    "name": "Mening shablon loyiham",
                    "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                    "envs": {"ADMIN_CHAT_ID": "123456789"},
                },
                description="Sotib olingan shablondan loyiha yaratish",
            )
        ]
