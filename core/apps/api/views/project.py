import hashlib
import json

from django.http import HttpResponse, StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models import BotModel, EnviromentModel, ProjectModel, RelaseModel
from core.apps.api.serializers.project import (
    CreateBotSerializer,
    CreateEnviromentSerializer,
    CreateProjectSerializer,
    CreateRelaseSerializer,
    ListBotSerializer,
    ListEnviromentSerializer,
    ListProjectSerializer,
    ListRelaseSerializer,
    RetrieveBotSerializer,
    RetrieveEnviromentSerializer,
    RetrieveProjectSerializer,
    RetrieveRelaseSerializer,
)
from core.apps.api.serializers.project.debug import CreateDebugSerializer, ListDebugSerializer
from core.apps.api.services.docker_service import deploy_debug_service, remove_service, service_logs_async
from core.apps.api.services.enviroment import project_enviroment


async def logs(request, pk):
    try:
        instance = await ProjectModel.objects.select_related("debug").aget(pk=pk)
        debug = instance.debug  # type: ignore
    except ProjectModel.DoesNotExist:
        raise NotFound()

    async def stream():
        if not debug.service_id:
            yield f"data: Container is not running\n\n"
            return

        async for line in service_logs_async(debug.service_id):
            if line[-1] == "\n":
                line = line[:-1]
            if line is None or line == "":
                continue
            yield f"data: {line}\n\n"

        yield f"data: Container is not running\n\n"

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
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

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
        "partial_update": CreateProjectSerializer,
        "debug": CreateDebugSerializer,
        "info": ListDebugSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(methods=["GET"], detail=True, url_name="info", url_path="info")
    def info(self, request, pk):
        instance = self.get_object().debug
        return Response(data=self.get_serializer(instance).data)

    @action(methods=["GET"], detail=True, url_name="debug", url_path="debug")
    def debug(self, request, pk):
        instance = self.get_object()
        debug = instance.debug
        hash = hashlib.md5(json.dumps(instance.flow).encode()).hexdigest()
        if debug.flow_hash == hash:
            return Response(data={"detail": _("No changes")})
        debug.flow_hash = hash
        debug.save()
        if debug.service_id:
            remove_service(debug.service_id)
        service = deploy_debug_service(
            instance.flow,
            instance.id,
            project_enviroment(instance.id),
        )
        debug.service_id = service.id
        debug.status = "initializing"
        debug.save()
        return Response(data={"detail": _("Updated")})


@extend_schema(tags=["bot"])
class BotView(BaseViewSetMixin, ModelViewSet):
    queryset = BotModel.objects.all()
    serializer_class = ListBotSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListBotSerializer,
        "retrieve": RetrieveBotSerializer,
        "create": CreateBotSerializer,
    }


@extend_schema(tags=["relase"])
class RelaseView(BaseViewSetMixin, ModelViewSet):
    queryset = RelaseModel.objects.all()
    serializer_class = ListRelaseSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListRelaseSerializer,
        "retrieve": RetrieveRelaseSerializer,
        "create": CreateRelaseSerializer,
    }


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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        project = self.request.query_params.get("project")
        if project is None:
            raise exceptions.ValidationError(detail={"project": _("project is required")})
        queryset = EnviromentModel.objects.filter(project=project, user=self.request.user)
        return queryset
