from django.shortcuts import get_object_or_404

from core.apps.cms.views._common import resolve_project
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiExample, extend_schema
from kubernetes.client.rest import ApiException
from rest_framework import exceptions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from core.apps.api.services.project import (
    copy_cms_collections,
    copy_collections,
    create_default_collections,
    default_flow,
)
from core.apps.cms.services.system_collections import ensure_system_collections

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import EnviromentModel, ProjectModel, RelaseModel
from core.apps.api.models.project import DebugModel
from core.apps.api.serializers.project import (
    CreateEnviromentSerializer,
    CreateProjectSerializer,
    CreateRelaseSerializer,
    ListEnviromentSerializer,
    ListProjectSerializer,
    ListRelaseSerializer,
    RetrieveEnviromentSerializer,
    RetrieveProjectSerializer,
    RetrieveRelaseSerializer,
)
from core.apps.api.serializers.project.debug import CreateDebugSerializer, ListDebugSerializer
from core.apps.api.serializers.project.project import CreateProjectFromTemplate
from core.apps.api.services.dashboard import DashboardService
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.running_bot_limit import check_running_bot_limit
from core.apps.api.services.kubernetes_service import deployment_logs_snapshot
from core.apps.api.services.enviroment import project_enviroment
from core.throttle.ip_throttle import DebugContainerThrottle, ReleaseCreateThrottle
from core.apps.api.services.webhook import set_webhook
from core.apps.api.exceptions.bot import BotTokenNotFound, ReleaseBotTokenNotFound
from core.apps.cms_legacy.models.cms import CollectionModel
from core.apps.template.models.order import TemplateOrderModel


def _error_response(desc, props):
    return OpenApiResponse(
        description=desc,
        response={"type": "object", "properties": props},
    )


class DeploymentUnavailable(exceptions.APIException):
    status_code = 503
    default_detail = _("Deployment service is temporarily unavailable")
    default_code = "deployment_unavailable"


def _deployment_error(exc: ApiException) -> DeploymentUnavailable:
    detail = _("Deployment service is temporarily unavailable")
    if exc.status in {401, 403}:
        detail = _("Deployment service is not authorized to manage Kubernetes resources")
    return DeploymentUnavailable(detail=detail)


@extend_schema(tags=["project"])
class ProjectView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListProjectSerializer
    permission_classes = [IsAuthenticated]
    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
        "partial_update": CreateProjectSerializer,
        "update": CreateProjectSerializer,
        "debug": CreateDebugSerializer,
        "info": ListDebugSerializer,
        "create_from_template": CreateProjectFromTemplate,
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.dashboardService = DashboardService()

    @extend_schema(
        summary="Loyihalar ro'yxati",
        description="Foydalanuvchiga tegishli barcha loyihalarni qaytaradi.",
        responses={200: ListProjectSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Loyiha ma'lumotlari",
        description="Berilgan ID bo'yicha loyihaning to'liq ma'lumotlarini qaytaradi.",
        responses={
            200: RetrieveProjectSerializer,
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Loyiha yaratish",
        description=(
            "Yangi loyiha yaratadi. Loyiha yaratish uchun alohida loyiha tarifi talab qilinmaydi; "
            "limitlar foydalanuvchi obunasi orqali boshqariladi."
        ),
        request=CreateProjectSerializer,
        responses={
            201: ListProjectSerializer,
            400: _error_response(
                "Validatsiya xatosi",
                {"name": {"type": "array", "items": {"type": "string"}, "example": ["Bu maydon to'ldirilishi shart."]}},
            ),
        },
        examples=[
            OpenApiExample(
                "Loyiha yaratish",
                value={"name": "Mening botim"},
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Loyihani yangilash",
        description=(
            "Loyiha ma'lumotlarini to'liq yangilaydi. Response YENGIL — to'liq flow "
            "qaytarilmaydi, faqat saqlanganini tasdiqlovchi {status, id, updated_at}."
        ),
        responses={
            200: OpenApiResponse(
                description="Saqlandi",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "ok"},
                        "id": {"type": "integer", "example": 12},
                        "updated_at": {"type": "string", "example": "2026-06-21T10:00:00Z"},
                    },
                },
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def update(self, request, *args, **kwargs):
        # Yengil response: flow saqlanadi, lekin to'liq flow QAYTARILMAYDI.
        # Constructor faqat 200 statusni tekshiradi — bandwidth tejaladi.
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "status": "ok",
                "id": instance.id,
                "updated_at": getattr(instance, "updated_at", None),
            }
        )

    @extend_schema(
        summary="Loyihani qisman yangilash",
        description=(
            "Loyiha ma'lumotlarini qisman yangilaydi (faqat yuborilgan maydonlar). "
            "Response YENGIL — to'liq flow qaytarilmaydi, faqat {status, id, updated_at}."
        ),
        responses={
            200: OpenApiResponse(
                description="Saqlandi",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "ok"},
                        "id": {"type": "integer", "example": 12},
                        "updated_at": {"type": "string", "example": "2026-06-21T10:00:00Z"},
                    },
                },
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Loyihani o'chirish",
        description="Loyihani va unga bog'liq barcha ma'lumotlarni o'chiradi.",
        responses={
            204: None,
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Prefetch

        latest_release_qs = RelaseModel.objects.order_by("-id")
        return (
            ProjectModel.objects
            .filter(owner=self.request.user)
            .select_related("debug")
            .prefetch_related(Prefetch("relases", queryset=latest_release_qs, to_attr="prefetched_relases"))
            .order_by("-id")
        )

    def get_object(self):
        raw = self.kwargs.get("pk")
        project = resolve_project(raw)
        if project is None:
            from rest_framework.exceptions import NotFound
            raise NotFound("Project not found")
        # Re-filter through the owner queryset to enforce ownership.
        return get_object_or_404(self.filter_queryset(self.get_queryset()), pk=project.pk)

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        project.flow = default_flow()
        project.save()
        create_default_collections(project)
        # cmsv2 schemas — make engine-written users/chat docs visible in the UI.
        ensure_system_collections(project)

    @extend_schema(
        summary="Shablondan loyiha yaratish",
        description=(
            "Sotib olingan shablondan yangi loyiha yaratadi.\n\n"
            "Shablon avval sotib olingan bo'lishi shart.\n\n"
            "Darhol birinchi release (v1) ham yaratiladi. Limitlar foydalanuvchi obunasi orqali boshqariladi."
        ),
        request=CreateProjectFromTemplate,
        responses={
            200: ListProjectSerializer,
            400: _error_response(
                "Xatolik",
                {
                    "detail": {"type": "string", "example": "template not purchased"},
                    "template": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Kechirasiz templateda muammo bor iltimos admin bilan bo'g'laning"],
                    },
                },
            ),
        },
        examples=[
            OpenApiExample(
                "Shablondan loyiha yaratish",
                value={
                    "template": 1,
                    "name": "Mening shablon botim",
                    "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                },
                request_only=True,
            )
        ],
    )
    @action(methods=["POST"], detail=False, url_name="create-from-template", url_path="create-from-template")
    def create_from_template(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = data.get("template")
        if not template.project.flow:
            raise exceptions.ValidationError(
                detail={"template": "Kechirasiz templateda muammo bor iltimos admin bilan bo'g'laning"}
            )
        order = TemplateOrderModel.objects.filter(template=template, user=request.user).first()
        if order is None or not order.payment_status:
            raise exceptions.ValidationError(detail=_("template not purchased"))

        # Limit tekshiruvi: yangi loyiha hali running emas, shuning uchun exclude kerak emas.
        check_running_bot_limit(request.user)

        instance = ProjectModel.objects.create(
            name=data.get("name"),
            flow=template.project.flow,
            owner=request.user,
        )
        EnviromentModel.objects.create(
            key="RELEASE_BOT_TOKEN", value=data.get("token"), project=instance, user=request.user
        )
        envs = data.get("envs") or {}
        for key, value in envs.items():
            EnviromentModel.objects.create(key=key, value=value, project=instance, user=request.user)
        RelaseModel.objects.create(project=instance, flow=instance.flow, version=1)
        # Legacy CMS schema copy (kept for backward compat).
        copy_collections(template.project, instance)
        # New CMS: register collections in cmsv2 + copy MongoDB catalog data so the
        # new bot actually has usable collections (visible in dashboard/MCP).
        copy_cms_collections(template.project, instance, flow=instance.flow)
        set_webhook(instance, "release")
        return Response(data=ListProjectSerializer(instance=instance).data)

    @extend_schema(
        summary="Dashboard statistikasi",
        description="Loyiha bo'yicha foydalanuvchilar soni va kunlik o'sish grafigini qaytaradi.",
        responses={
            200: OpenApiResponse(
                description="Statistika ma'lumotlari",
                response={
                    "type": "object",
                    "properties": {
                        "total_users": {"type": "integer", "example": 1500},
                        "daily_users": {"type": "integer", "example": 43},
                        "chart": {
                            "type": "object",
                            "properties": {
                                "new_users": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "date": {"type": "string", "example": "2026-02-28"},
                                            "value": {"type": "integer", "example": 43},
                                        },
                                    },
                                }
                            },
                        },
                    },
                },
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_name="dashboard", url_path="dashboard")
    def dashboard(self, request, pk):
        project = self.get_object()
        collection = get_object_or_404(CollectionModel, project=project, name="users")
        self.dashboardService.set_collection(collection)
        return Response(
            data={
                "chart": {
                    "new_users": self.dashboardService.get_user_chart(),
                },
                "total_users": self.dashboardService.users_count(),
                "daily_users": self.dashboardService.daily_users(),
            }
        )

    @extend_schema(
        summary="Collab WS token",
        description=(
            "Real-time kollaborativ tahrirlash uchun project_id claim'li qisqa "
            "muddatli WS token. Faqat loyiha egasi oladi (get_queryset egalik "
            "bo'yicha filtrlaydi). Konstruktor shu token bilan websocket-golang'ga "
            "ulanib `project_<id>` xonasiga kiradi."
        ),
    )
    @action(methods=["GET"], detail=True, url_name="collab-token", url_path="collab-token")
    def collab_token(self, request, pk):
        from rest_framework_simplejwt.tokens import AccessToken

        project = self.get_object()  # egasi bo'lmasa get_queryset 404 qaytaradi
        token = AccessToken.for_user(request.user)
        token["project_id"] = project.id
        return Response(data={"token": str(token), "room": "project_%s" % project.id})

    @extend_schema(
        summary="Bot tokenini o'rnatish (telegram credential)",
        description=(
            "Telegram bot tokenini qabul qiladi, getMe orqali tekshiradi, owner-scoped "
            "telegram credential yaratadi/yangilaydi va deploy uchun RELEASE_BOT_TOKEN "
            "(secret) env'ini o'rnatadi. Ishga tushurish (release)dan oldin chaqiriladi."
        ),
        request={"application/json": {"type": "object", "properties": {"token": {"type": "string"}}}},
    )
    @action(methods=["POST"], detail=True, url_name="set-bot-token", url_path="set-bot-token")
    def set_bot_token(self, request, pk):
        from telebot import TeleBot
        from core.apps.credentials.models import Credential
        from core.apps.credentials.services import crypto

        project = self.get_object()  # owner-checked via get_queryset
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response({"detail": _("Token kiritilmagan")}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the token and grab the bot username for a nice credential name.
        try:
            bot_username = TeleBot(token).get_me().username
        except Exception:
            return Response(
                {"detail": _("Token noto'g'ri yoki Telegram'ga ulanib bo'lmadi")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cred_name = ("@%s" % bot_username) if bot_username else (project.name or "Bot token")
        data_encrypted = crypto.encrypt({"bot_token": token})
        try:
            existing = Credential.objects.filter(
                owner=request.user, name=cred_name, deleted_at__isnull=True
            ).first()
            if existing:
                existing.type_key = "telegram"
                existing.data_encrypted = data_encrypted
                existing.save()
            else:
                Credential.objects.create(
                    owner=request.user, name=cred_name, type_key="telegram",
                    data_encrypted=data_encrypted,
                )
        except Exception:
            # Credential is for management; the env below is what the deploy actually reads.
            pass

        # Deploy reads RELEASE_BOT_TOKEN — keep it in sync (marked secret so the UI masks it).
        EnviromentModel.objects.update_or_create(
            project=project,
            key="RELEASE_BOT_TOKEN",
            defaults={"value": token, "user": request.user, "secret": True},
        )
        return Response({"detail": _("Saqlandi"), "username": bot_username})

    @extend_schema(
        summary="Debug holati",
        description="Loyihaning debug konteynerining joriy holati va ma'lumotlarini qaytaradi.",
        responses={
            200: ListDebugSerializer,
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_name="info", url_path="info")
    def info(self, request, pk):
        instance = self.get_object().debug
        return Response(data=self.get_serializer(instance).data)

    @extend_schema(
        summary="Debug konteynerini to'xtatish",
        description="Loyihaning ishlab turgan debug konteynerini to'xtatadi.",
        responses={
            200: OpenApiResponse(
                description="Muvaffaqiyatli to'xtatildi",
                response={"type": "object", "properties": {"detail": {"type": "string", "example": "Stopped"}}},
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_path="stop", url_name="stop")
    def stop(self, request, pk):
        instance = self.get_object()
        remove_service(instance.debug.service_id)
        instance.debug.status = ContainerStatusEnum.STOPPING.value
        instance.debug.save()
        return Response(data={"detail": _("Stopped")})

    @extend_schema(
        summary="Debug rejimini ishga tushirish",
        description=(
            "Loyihaning debug konteynerini ishga tushiradi.\n\n"
            "Debug rejimi test maqsadida ishlatiladi va real foydalanuvchilarga ta'sir qilmaydi."
        ),
        request=CreateDebugSerializer,
        responses={
            200: OpenApiResponse(
                description="Debug muvaffaqiyatli ishga tushirildi",
                response={"type": "object", "properties": {"detail": {"type": "string", "example": "Updated"}}},
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_name="debug", url_path="debug", throttle_classes=[DebugContainerThrottle])
    def debug(self, request, pk):
        instance = self.get_object()
        check_running_bot_limit(request.user, exclude_project_id=instance.pk)
        debug, _created = DebugModel.objects.get_or_create(project=instance)
        try:
            service = deploy_service(
                instance,
                "debug",
                instance.flow,
                instance.id,
                list(project_enviroment(instance.id)),
                webhook_uuid=str(instance.debug_webhook_uuid),
            )
        except ApiException as exc:
            debug.status = ContainerStatusEnum.FAILED.value
            debug.save(update_fields=["status", "updated_at"])
            raise _deployment_error(exc) from exc
        debug.service_id = service.metadata.name
        debug.status = "initializing"
        debug.save()
        return Response(data={"detail": _("Updated")})

    @extend_schema(
        summary="Loyiha uchun yoqilgan modullar ro'yxati",
        responses={200: "ProjectModuleSerializer(many=True)"},
    )
    @action(methods=["GET", "POST"], detail=True, url_path="modules", url_name="modules")
    def modules(self, request, pk):
        from core.apps.api.views.module import project_module_list, project_module_enable

        project = self.get_object()
        if request.method == "GET":
            return project_module_list(request, project)
        return project_module_enable(request, project)

    @extend_schema(
        summary="Modulni o'chirish",
    )
    @action(methods=["DELETE"], detail=True, url_path="modules/(?P<slug>[^/.]+)", url_name="module-disable")
    def module_disable(self, request, pk, slug):
        from core.apps.api.views.module import project_module_disable

        project = self.get_object()
        return project_module_disable(request, project, slug)

    @extend_schema(
        summary="Constructor uchun modul manifestlari",
        responses={200: {"type": "object", "properties": {"manifests": {"type": "array"}}}},
    )
    @action(methods=["GET"], detail=True, url_path="module-manifests", url_name="module-manifests")
    def module_manifests(self, request, pk):
        from core.apps.api.views.module import project_module_manifests_view

        project = self.get_object()
        return project_module_manifests_view(request, project)

    @extend_schema(
        summary="Engine uchun modules.json ma'lumotlari",
        responses={200: {"type": "object", "properties": {"modules": {"type": "array"}}}},
    )
    @action(methods=["GET"], detail=True, url_path="modules-for-engine", url_name="modules-for-engine")
    def modules_for_engine(self, request, pk):
        from core.apps.api.views.module import project_modules_for_engine_view

        project = self.get_object()
        return project_modules_for_engine_view(request, project)

    @extend_schema(
        summary="Debug bot loglarini olish (snapshot)",
        description=(
            "Loyihaning DEBUG konteyneri pod loglarining oxirgi N qatorini qaytaradi. "
            "Streaming emas — JSON snapshot (release logs bilan bir xil format)."
        ),
        parameters=[
            OpenApiParameter(
                name="tail",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Oxirgi nechta qator (default 200, max 2000).",
            ),
            OpenApiParameter(
                name="since_seconds",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Faqat oxirgi N soniya ichidagi qatorlar (ixtiyoriy).",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Log snapshot",
                response={
                    "type": "object",
                    "properties": {
                        "pod_name": {"type": "string", "nullable": True},
                        "lines": {"type": "array", "items": {"type": "string"}},
                        "truncated": {"type": "boolean"},
                    },
                },
            ),
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_path="debug/logs", url_name="debug-logs")
    def debug_logs(self, request, pk):
        instance = self.get_object()
        debug = DebugModel.objects.filter(project=instance).first()
        if debug is None or not debug.service_id:
            return Response(
                data={"pod_name": None, "lines": [], "truncated": False, "detail": _("Debug is not running")},
            )
        try:
            tail = int(request.query_params.get("tail", 200))
        except (TypeError, ValueError):
            tail = 200
        since_param = request.query_params.get("since_seconds")
        try:
            since = int(since_param) if since_param is not None else None
        except (TypeError, ValueError):
            since = None
        snapshot = deployment_logs_snapshot(debug.service_id, tail_lines=tail, since_seconds=since)
        return Response(data=snapshot)


@extend_schema(tags=["relase"])
class ReleaseView(BaseViewSetMixin, CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = ListRelaseSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListRelaseSerializer,
        "retrieve": RetrieveRelaseSerializer,
        "create": CreateRelaseSerializer,
    }

    def get_queryset(self):
        queryset = RelaseModel.objects.order_by("-id").filter(project__owner=self.request.user)
        if self.action in ["list"]:
            project_raw = self.request.query_params.get("project")
            if project_raw is None:
                raise exceptions.ValidationError(detail={"project": [_("project is required")]})
            project = resolve_project(project_raw)
            if project is None:
                raise exceptions.ValidationError(detail={"project": [_("project not found")]})
            queryset = queryset.filter(project_id=project.pk)
        return queryset

    def get_throttles(self):
        if self.action in ("create", "rollback"):
            return [ReleaseCreateThrottle()]
        return super().get_throttles()

    @extend_schema(
        summary="Releaselar ro'yxati",
        description="Berilgan loyiha bo'yicha barcha releaselarni qaytaradi.",
        parameters=[
            OpenApiParameter(
                name="project",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Loyiha ID si (majburiy)",
            )
        ],
        responses={
            200: ListRelaseSerializer(many=True),
            400: _error_response(
                "project parametri yo'q",
                {"project": {"type": "array", "items": {"type": "string"}, "example": ["project is required"]}},
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Release ma'lumotlari",
        description="Berilgan ID bo'yicha releasening to'liq ma'lumotlarini (flow ham kiritilgan holda) qaytaradi.",
        responses={
            200: RetrieveRelaseSerializer,
            404: _error_response("Release topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Yangi release yaratish",
        description=(
            "Loyiha uchun yangi release yaratadi va uni deploy qiladi.\n\n"
            "**Tarif qoidalari:**\n"
            "- **Birinchi release** — `plan_id` majburiy:\n"
            "  - Agar siz hech qaysi loyihangizda FREE plan bilan release qilmagan bo'lsangiz → "
            "FREE yoki pulli plan tanlash mumkin.\n"
            "  - Agar siz biror loyihangizda FREE plan bilan allaqachon release qilgan bo'lsangiz → "
            "pulli tarif tanlash **majburiy**.\n"
            "  - Pulli tarif tanlanganda balansdan bir martalik to'lov yechiladi va plan loyihaga biriktiriladi.\n\n"
            "- **Keyingi releaselar** — `plan_id` talab qilinmaydi. Plan allaqachon loyihaga biriktirilgan, "
            "oylik to'lov avtomatik yechib turiladi.\n\n"
            "**Versiya** avtomatik oshiriladi."
        ),
        request=CreateRelaseSerializer,
        responses={
            201: ListRelaseSerializer,
            400: OpenApiResponse(
                description="Validatsiya xatosi",
                response={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": [
                                "Birinchi release uchun tarif tanlash majburiy",
                                "Siz allaqachon bepul tarifdan foydalangansiz. Pulli tarif tanlash majburiy",
                                "Balansingiz yetarli emas. Kerakli: 50000, Mavjud: 10000",
                            ],
                        },
                        "project": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["Bu maydon to'ldirilishi shart."],
                        },
                    },
                },
            ),
        },
        examples=[
            OpenApiExample(
                "Birinchi release (FREE tarif)",
                value={"project": 1, "plan_id": 1},
                request_only=True,
                description="Birinchi marta release qilish — FREE tarif tanlangan holda",
            ),
            OpenApiExample(
                "Birinchi release (pulli tarif)",
                value={"project": 1, "plan_id": 2},
                request_only=True,
                description="Birinchi marta release qilish — pulli tarif tanlangan holda (balansdan yechiladi)",
            ),
            OpenApiExample(
                "Keyingi release",
                value={"project": 1},
                request_only=True,
                description="Loyihada allaqachon release bor — plan_id talab qilinmaydi",
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (BotTokenNotFound, ReleaseBotTokenNotFound):
            # First release without a bot token — tell the dashboard to ask for a
            # Telegram credential instead of returning a 500.
            return Response(
                {
                    "detail": _("Ishga tushurishdan oldin Telegram bot tokenini kiriting."),
                    "code": "bot_token_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ApiException as exc:
            raise _deployment_error(exc) from exc

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        check_running_bot_limit(self.request.user, exclude_project_id=project.pk if project else None)

        serializer.validated_data.pop("plan_id", None)
        serializer.validated_data.pop("months", None)

        set_webhook(project, "release")
        relase = RelaseModel.objects.filter(project=project).last()
        version = 1 if relase is None else relase.version

        serializer.save(version=version + 1, flow=project.flow)

    @extend_schema(
        summary="Releaseni to'xtatish",
        description="Ishlab turgan release konteynerini to'xtatadi.",
        responses={
            200: OpenApiResponse(
                description="Muvaffaqiyatli to'xtatildi",
                response={"type": "object", "properties": {"detail": {"type": "string", "example": "Stopped"}}},
            ),
            404: _error_response("Release topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_path="stop", url_name="stop")
    def stop(self, request, pk):
        instance = self.get_object()
        remove_service(instance.service_id)
        # Deployment sinxron o'chirildi — STOPPED'ga o'tishni watcher'ning DELETED
        # eventiga qoldirmaymiz (poyga qilib STOPPING'da qotib qolardi).
        instance.status = ContainerStatusEnum.STOPPED.value
        instance.save()
        return Response(data={"detail": _("Stopped")})

    @extend_schema(
        summary="Eski release'ga qaytarish (rollback)",
        description=(
            "Tanlangan release'ning flow snapshot'i bilan YANGI release yaratadi va deploy qiladi. "
            "Loyihaning joriy (draft) flow'i ham shu snapshotga tiklanadi, shunda konstruktor jonli "
            "versiyaga mos bo'ladi. Versiya avtomatik oshiriladi; eski ishlab turgan release to'xtatiladi."
        ),
        request=None,
        responses={
            201: ListRelaseSerializer,
            404: _error_response("Release topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["POST"], detail=True, url_path="rollback", url_name="rollback")
    def rollback(self, request, pk):
        source = self.get_object()  # egalik get_queryset orqali tekshiriladi (begona loyiha → 404)
        project = source.project
        check_running_bot_limit(request.user, exclude_project_id=project.pk)
        set_webhook(project, "release")

        # Eski release flow snapshot'ini joriy draft'ga tiklaymiz (konstruktor mos bo'lsin).
        project.flow = source.flow
        project.save(update_fields=["flow"])

        last = RelaseModel.objects.filter(project=project).order_by("version").last()
        version = 1 if last is None else last.version + 1
        # create() RelaseSignal'ni ishga tushiradi: yangi flow'ni deploy qiladi +
        # eski ishlab turgan release'larni STOPPED qiladi.
        release = RelaseModel.objects.create(project=project, version=version, flow=source.flow)
        return Response(ListRelaseSerializer(release).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Release loglarini olish (snapshot)",
        description=(
            "Bu release uchun ishlayotgan pod loglarining oxirgi N qatorini qaytaradi. "
            "Streaming emas — JSON snapshot. Real-time stream uchun /sse/.../logs/ ishlatiladi."
        ),
        parameters=[
            OpenApiParameter(
                name="tail",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Oxirgi nechta qator (default 200, max 2000).",
            ),
            OpenApiParameter(
                name="since_seconds",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Faqat oxirgi N soniyadagi qatorlar.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Log qatorlari",
                response={
                    "type": "object",
                    "properties": {
                        "pod_name": {"type": "string", "nullable": True},
                        "lines": {"type": "array", "items": {"type": "string"}},
                        "truncated": {"type": "boolean"},
                    },
                },
            ),
            404: _error_response("Release topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    @action(methods=["GET"], detail=True, url_path="logs", url_name="logs")
    def logs(self, request, pk):
        instance = self.get_object()
        if not instance.service_id:
            return Response(
                data={"pod_name": None, "lines": [], "truncated": False, "detail": _("Service is not deployed")},
            )
        try:
            tail = int(request.query_params.get("tail", 200))
        except (TypeError, ValueError):
            tail = 200
        since_param = request.query_params.get("since_seconds")
        try:
            since = int(since_param) if since_param is not None else None
        except (TypeError, ValueError):
            since = None
        snapshot = deployment_logs_snapshot(instance.service_id, tail_lines=tail, since_seconds=since)
        return Response(data=snapshot)


@extend_schema(tags=["enviroment"])
class EnviromentView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListEnviromentSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListEnviromentSerializer,
        "retrieve": RetrieveEnviromentSerializer,
        "create": CreateEnviromentSerializer,
    }

    def get_object(self):
        return get_object_or_404(
            self.filter_queryset(self.get_queryset()),
            key=self.kwargs["pk"],
        )

    def perform_create(self, serializer):
        key = serializer.validated_data["key"]
        project = serializer.validated_data["project"]
        value = serializer.validated_data["value"]
        secret = serializer.validated_data.get("secret", False)
        obj, _ = EnviromentModel.objects.update_or_create(
            key=key,
            project=project,
            defaults={"value": value, "secret": secret, "user": self.request.user},
        )
        serializer.instance = obj

    def get_queryset(self):
        project_raw = self.request.query_params.get("project")
        if project_raw is None:
            raise exceptions.ValidationError(detail={"project": [_("project is required")]})
        # project_raw may be an integer pk OR a UUID string.
        project = resolve_project(project_raw)
        if project is None:
            raise exceptions.ValidationError(detail={"project": [_("project not found")]})
        return EnviromentModel.objects.filter(project_id=project.pk, user=self.request.user)
