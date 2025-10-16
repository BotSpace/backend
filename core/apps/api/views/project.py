import hashlib
import json

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import EnviromentModel, ProjectModel, RelaseModel
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
from core.apps.api.services.docker_service import deploy_service, remove_service, service_logs_async
from core.apps.api.services.enviroment import project_enviroment, validate_debug_enviroment


async def logs(request, service_id):
    async def stream():
        async for line in service_logs_async(service_id):
            if line[-1] == "\n":
                line = line[:-1]
            if line is None or line == "":
                continue
            yield f"data: {line}\n\n"

        yield "data: Container is not running\n\n"

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
    response["Access-Control-Allow-Credentials"] = "false"
    return response


@extend_schema(tags=["project"])
class ProjectView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProjectModel.objects.order_by("-id").all()
        if self.request.user.is_authenticated:
            return queryset.filter(owner=self.request.user)
        return queryset.none()

    def get_object(self):
        return get_object_or_404(self.filter_queryset(self.get_queryset()), pk=self.kwargs.get("pk"))

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
        "partial_update": CreateProjectSerializer,
        "update": CreateProjectSerializer,
        "debug": CreateDebugSerializer,
        "info": ListDebugSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            flow={"nodes": [], "edges": []},
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
        if not validate_debug_enviroment(pk):
            return Response(data={"detail": _("debug uchun enviroment to'liq emas")}, status=400)
        instance = self.get_object()
        debug = instance.debug
        # hash = hashlib.md5(json.dumps(instance.flow).encode()).hexdigest()
        # if debug.flow_hash == hash:
        #     return Response(data={"detail": _("No changes")})
        # debug.flow_hash = hash
        # debug.save()
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
class RelaseView(BaseViewSetMixin, CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = ListRelaseSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListRelaseSerializer,
        "retrieve": RetrieveRelaseSerializer,
        "create": CreateRelaseSerializer,
    }

    def get_queryset(self):
        queryset = RelaseModel.objects.order_by("-id")
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
