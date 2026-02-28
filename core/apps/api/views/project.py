from django.shortcuts import get_object_or_404
from core.apps.payment.services.balance import subtract_balance
from core.apps.api.models import ProjectPlanModel
from core.apps.api.enums.plan import PlanStatus
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiExample, extend_schema
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from core.apps.api.services.project import copy_collections, create_default_collections, default_flow

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import EnviromentModel, ProjectModel, RelaseModel, PlanModel
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
from core.apps.api.services.enviroment import project_enviroment
from core.apps.api.services.webhook import set_webhook
from core.apps.cms.models.cms import CollectionModel
from core.apps.template.models.order import TemplateOrderModel


_error_response = lambda desc, props: OpenApiResponse(
    description=desc,
    response={"type": "object", "properties": props},
)


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
            "Yangi loyiha yaratadi. Loyiha yaratish **bepul va limitsiz** — plan talab qilinmaydi.\n\n"
            "Loyiha avtomatik ravishda **FREE** tarifga biriktiriladi.\n\n"
            "Tarif birinchi **release** qo'shilganda tanlanadi."
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
        description="Loyiha ma'lumotlarini to'liq yangilaydi.",
        responses={
            200: ListProjectSerializer,
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Loyihani qisman yangilash",
        description="Loyiha ma'lumotlarini qisman yangilaydi (faqat yuborilgan maydonlar o'zgaradi).",
        responses={
            200: ListProjectSerializer,
            404: _error_response("Loyiha topilmadi", {"detail": {"type": "string", "example": "Not found."}}),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

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
        return ProjectModel.objects.order_by("-id").filter(owner=self.request.user)

    def get_object(self):
        return get_object_or_404(self.filter_queryset(self.get_queryset()), pk=self.kwargs.get("pk"))

    def perform_create(self, serializer):
        free_plan, _ = PlanModel.objects.get_or_create(
            name="free",
            defaults={"is_active": True, "price": 0},
        )

        project = serializer.save(owner=self.request.user)
        project.flow = default_flow()
        project.save()
        ProjectPlanModel.objects.create(project=project, plan=free_plan, status=PlanStatus.ACTIVE, current_users=0)
        create_default_collections(project)

    @extend_schema(
        summary="Shablondan loyiha yaratish",
        description=(
            "Sotib olingan shablondan yangi loyiha yaratadi.\n\n"
            "Shablon avval sotib olingan bo'lishi shart.\n\n"
            "Loyiha FREE tarifga biriktiriladi va darhol birinchi release (v1) ham yaratiladi."
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

        free_plan, _ = PlanModel.objects.get_or_create(
            name="free",
            defaults={"is_active": True, "price": 0},
        )

        instance = ProjectModel.objects.create(
            name=data.get("name"),
            flow=template.project.flow,
            owner=request.user,
        )
        ProjectPlanModel.objects.create(project=instance, plan=free_plan, status=PlanStatus.ACTIVE, current_users=0)
        EnviromentModel.objects.create(
            key="RELEASE_BOT_TOKEN", value=data.get("token"), project=instance, user=request.user
        )
        RelaseModel.objects.create(project=instance, flow=instance.flow, version=1)
        copy_collections(template.project, instance)
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
    @action(methods=["GET"], detail=True, url_name="debug", url_path="debug")
    def debug(self, request, pk):
        instance = self.get_object()
        debug = instance.debug
        service = deploy_service(
            instance,
            "debug",
            instance.flow,
            instance.id,
            list(project_enviroment(instance.id)),
            webhook_uuid=str(instance.debug_webhook_uuid),
        )
        debug.service_id = service.metadata.name
        debug.status = "initializing"
        debug.save()
        return Response(data={"detail": _("Updated")})


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
            project_id = self.request.query_params.get("project")
            if project_id is None:
                raise exceptions.ValidationError(detail={"project": [_("project is required")]})
            queryset = queryset.filter(project_id=project_id)
        return queryset

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
        return super().create(request, *args, **kwargs)

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
        instance.status = ContainerStatusEnum.STOPPING.value
        instance.save()
        return Response(data={"detail": _("Stopped")})

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        plan = serializer.validated_data.pop("_plan", None)

        set_webhook(project, "release")
        relase = RelaseModel.objects.filter(project=project).last()
        version = 1 if relase is None else relase.version

        # Birinchi release: plan biriktiriladi va kerak bo'lsa pul yechiladi
        if plan is not None:
            if plan.price > 0:
                subtract_balance(
                    self.request.user, plan.price, comment=f"Tarif to'lovi: {plan.get_name_display()}"
                )
            project.plan_subscription.plan = plan
            project.plan_subscription.save(update_fields=["plan"])

        serializer.save(version=version + 1, flow=project.flow)


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
        serializer.save(user=self.request.user)

    def get_queryset(self):
        project = self.request.query_params.get("project")
        if project is None:
            raise exceptions.ValidationError(detail={"project": [_("project is required")]})
        queryset = EnviromentModel.objects.filter(project=project, user=self.request.user)
        return queryset
