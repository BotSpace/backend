import asyncio
import hashlib
import json

from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models import BotModel, ProjectModel, RelaseModel
from core.apps.api.serializers.project import (
    CreateBotSerializer,
    CreateProjectSerializer,
    CreateRelaseSerializer,
    ListBotSerializer,
    ListProjectSerializer,
    ListRelaseSerializer,
    RetrieveBotSerializer,
    RetrieveProjectSerializer,
    RetrieveRelaseSerializer,
)
from core.apps.api.serializers.project.project import DebugProjectSerializer


def logs(request, pk):
    try:
        instance = ProjectModel.objects.get(pk=pk)
    except ProjectModel.DoesNotExist:
        return NotFound()

    async def stream():
        for i in range(5):
            await asyncio.sleep(1)
            yield f"data: {i}\n\n"

    # if not instance.is_debug_active:
    #     return Response(data={"detail": _("Container not running")})
    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # 🔥 Nginx bufferini o‘chiradi
    return response


@extend_schema(tags=["project"])
class ProjectView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProjectModel.objects.all()
        if self.request.user.is_authenticated:
            return queryset.filter(owner=self.request.user)
        return queryset.none()

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
        "partial_update": CreateProjectSerializer,
        "debug": DebugProjectSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(methods=["PATCH"], detail=True, url_name="debug", url_path="debug")
    def debug(self, request, pk):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = self.get_object()
        hash = hashlib.md5(json.dumps(ser.data.get("flow")).encode()).hexdigest()
        if instance.flow_hash == hash:
            return Response(data={"detail": _("No changes")})
        instance.flow_hash = hash
        instance.save()
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
