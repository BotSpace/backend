import base64
import gzip
import json

from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample
from core.apps.api.models import ProjectModel
from core.apps.api.models.project import EnviromentModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer
from core.apps.api.serializers.project.relase import ListRelaseSerializer
from core.apps.api.services.dashboard import DashboardService
from core.apps.cms_legacy.services.mongo import get_project_collection
from core.apps.template.models import TemplateModel


def flow_to_gz(flow) -> str:
    """flow (dict/list) → base64(gzip(json.dumps(flow)))"""
    raw = json.dumps(flow, ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(raw)
    return base64.b64encode(compressed).decode("ascii")


def gz_to_flow(flow_gz: str):
    """base64(gzip(json)) → dict/list. ValueError on bad input."""
    try:
        compressed = base64.b64decode(flow_gz)
    except Exception as exc:
        raise ValueError("flow_gz: base64 decode xatosi") from exc
    try:
        raw = gzip.decompress(compressed)
    except Exception as exc:
        raise ValueError("flow_gz: gzip decompress xatosi") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("flow_gz: JSON parse xatosi") from exc


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
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        compress = request and request.query_params.get("compress") in ("1", "true", "True")
        if compress:
            flow_value = data.get("flow")
            data["flow_gz"] = flow_to_gz(flow_value)
            data["flow"] = None
        return data

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
    flow_gz = serializers.CharField(required=False, write_only=True, allow_blank=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        flow_gz = attrs.pop("flow_gz", None)
        if flow_gz is not None:
            try:
                attrs["flow"] = gz_to_flow(flow_gz)
            except ValueError as exc:
                raise serializers.ValidationError({"flow_gz": str(exc)}) from exc
        return attrs

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
            "flow_gz",
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
    mode = serializers.ChoiceField(
        choices=["release", "debug"],
        default="release",
        required=False,
        help_text="release: token/managed_bot_id majburiy, darhol release yaratiladi. "
        "debug: tokensiz, DEBUG konteyner (platforma TEST bot tokeni bilan) ishga tushadi.",
    )
    token = serializers.CharField(max_length=255, required=False, allow_blank=True, default="", help_text="Release bot tokeni")
    managed_bot_id = serializers.IntegerField(required=False, min_value=1, help_text="Managed bot ID (token o'rniga)")
    envs = serializers.DictField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=dict,
        help_text="Template'ning envs kalitlari uchun qiymatlar: {KEY: value}",
    )
    credentials = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=dict,
        help_text="Logical credential key → real credential_id mapping: {key: id}",
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        mode = attrs.get("mode") or "release"
        token = (attrs.get("token") or "").strip()
        managed_bot_id = attrs.get("managed_bot_id")
        if mode == "release" and not token and not managed_bot_id:
            raise serializers.ValidationError(
                {"token": "token yoki managed_bot_id dan biri majburiy"}
            )

        template = attrs.get("template")
        spec = template.spec or {}

        # Env validatsiya
        envs = attrs.get("envs", {})
        required_envs = spec.get("envs") or template.required_envs or []
        missing_envs = [
            item["key"] for item in required_envs
            if isinstance(item, dict) and item.get("key") and item.get("required", True)
            and not envs.get(item["key"], "").strip()
        ]
        if missing_envs:
            raise serializers.ValidationError(
                {"envs": [f"{key} majburiy" for key in missing_envs]}
            )

        # Credential validatsiya — spec'da required=True bo'lganlar SHART
        credentials = attrs.get("credentials", {})
        spec_creds = spec.get("credentials", [])
        missing_creds = [
            c["key"] for c in spec_creds
            if isinstance(c, dict) and c.get("required", True) and not credentials.get(c["key"])
        ]
        if missing_creds:
            raise serializers.ValidationError(
                {"credentials": [f"{key} credential majburiy" for key in missing_creds]}
            )

        # Ownership: user faqat O'ZINING credential'ini map qila oladi (IDOR himoyasi)
        if credentials:
            from core.apps.credentials.models.credential import Credential

            user = self.context["request"].user
            owned = set(
                Credential.objects.filter(
                    id__in=list(credentials.values()), owner=user, deleted_at__isnull=True
                ).values_list("id", flat=True)
            )
            bad = [key for key, cid in credentials.items() if cid not in owned]
            if bad:
                raise serializers.ValidationError(
                    {"credentials": [f"{key}: credential topilmadi yoki sizga tegishli emas" for key in bad]}
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
                    "credentials": {"openai": 42},
                },
                description="Sotib olingan shablondan loyiha yaratish",
            )
        ]
