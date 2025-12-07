# type: ignore
from django.shortcuts import get_object_or_404
from core.apps.payment.services.balance import subtract_balance
from core.apps.api.models import ProjectPlanModel
from core.apps.api.enums.plan import PlanStatus
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from core.apps.api.services.project import default_flow

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
        summary="Loyiha yaratish",
        description="Yangi loyiha yaratadi. Plan tanlash majburiy va balansingiz yetarli bo'lishi kerak.",
        responses={
            201: ListProjectSerializer,
            400: OpenApiResponse(
                description="Xatolik: plan noto'g'ri yoki balans yetarli emas",
                response={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["Balansingiz yetarli emas. Kerakli: 50000, Mavjud: 10000"],
                        }
                    },
                },
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return ProjectModel.objects.order_by("-id").filter(owner=self.request.user)

    def get_object(self):
        return get_object_or_404(self.filter_queryset(self.get_queryset()), pk=self.kwargs.get("pk"))

    def perform_create(self, serializer):
        plan_id = serializer.validated_data.get("plan_id")
        plan = PlanModel.objects.get(id=plan_id, is_active=True)

        if plan.price > 0:
            subtract_balance(self.request.user, plan.price, comment=f"Tarif to'lovi: {plan.get_name_display()}")

        project = serializer.save(owner=self.request.user)
        project.flow = default_flow()
        project.save()
        ProjectPlanModel.objects.create(project=project, plan=plan, status=PlanStatus.ACTIVE, current_users=0)

    @extend_schema(
        summary="Shablondan loyiha yaratish",
        description="Sotib olingan shablondan yangi loyiha yaratadi. Plan talab qilinadi va balans tekshiriladi.",
        request=CreateProjectFromTemplate,
        responses={
            200: ListProjectSerializer,
            400: OpenApiResponse(
                description="Xatolik: shablon sotib olinmagan, plan noto'g'ri yoki balans yetarli emas",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string", "example": "template not purchased"},
                        "plan_id": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["Balansingiz yetarli emas. Kerakli: 50000, Mavjud: 10000"],
                        },
                    },
                },
            ),
        },
    )
    @action(methods=["POST"], detail=False, url_name="create-from-template", url_path="create-from-template")
    def create_from_template(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = data.get("template")
        order = TemplateOrderModel.objects.filter(template=template, user=request.user).first()
        if order is None or not order.payment_status:
            raise exceptions.ValidationError(detail=_("template not purchased"))

        plan_id = data.get("plan_id")
        plan = PlanModel.objects.get(id=plan_id, is_active=True)

        if plan.price > 0:
            subtract_balance(request.user, plan.price, comment=f"Tarif to'lovi: {plan.get_name_display()}")

        instance = ProjectModel.objects.create(
            name=data.get("name"),
            flow=template.flow,
            owner=request.user,
        )
        ProjectPlanModel.objects.create(project=instance, plan=plan, status=PlanStatus.ACTIVE, current_users=0)
        EnviromentModel.objects.create(
            key="RELEASE_BOT_TOKEN", value=data.get("token"), project=instance, user=request.user
        )
        RelaseModel.objects.create(project=instance, flow=instance.flow, version=1)
        return Response(data=ListProjectSerializer(instance=instance).data)

    @extend_schema(
        summary="Dashboard api",
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "total_users": {"type": "integer", "example": 100},
                        "daily_users": {"type": "integer", "example": 50},
                        "chart": {
                            "type": "object",
                            "properties": {
                                "new_users": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "date": {"type": "string", "example": "2025-11-22"},
                                            "value": {"type": "integer", "example": 100},
                                        },
                                    },
                                }
                            },
                        },
                    },
                },
            ),
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

    @action(methods=["GET"], detail=True, url_name="info", url_path="info")
    def info(self, request, pk):
        instance = self.get_object().debug
        return Response(data=self.get_serializer(instance).data)

    @action(methods=["GET"], detail=True, url_path="stop", url_name="stop")
    def stop(self, request, pk):
        instance = self.get_object()
        remove_service(instance.debug.service_id)
        instance.debug.status = ContainerStatusEnum.STOPPING.value
        instance.debug.save()
        return Response(data={"detail": _("Stopped")})

    @action(methods=["GET"], detail=True, url_name="debug", url_path="debug")
    def debug(self, request, pk):
        instance = self.get_object()
        debug = instance.debug
        if debug.service_id:
            remove_service(debug.service_id)
        service = deploy_service(
            instance,
            "debug",
            instance.flow,
            instance.id,
            list(project_enviroment(instance.id)),
        )
        debug.service_id = service.id
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

    @action(methods=["GET"], detail=True, url_path="stop", url_name="stop")
    def stop(self, request, pk):
        instance = self.get_object()
        remove_service(instance.service_id)
        instance.status = ContainerStatusEnum.STOPPING.value
        instance.save()
        return Response(data={"detail": _("Stopped")})

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        set_webhook(project, "release")
        relase = RelaseModel.objects.filter(
            project=project,
        ).last()
        if relase is None:
            version = 1
        else:
            version = relase.version

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
