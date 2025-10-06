from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models import BotModel, FlowModel, ProjectModel, RelaseModel
from core.apps.api.serializers.project import (
    CreateBotSerializer,
    CreateFlowSerializer,
    CreateProjectSerializer,
    CreateRelaseSerializer,
    ListBotSerializer,
    ListFlowSerializer,
    ListProjectSerializer,
    ListRelaseSerializer,
    RetrieveBotSerializer,
    RetrieveFlowSerializer,
    RetrieveProjectSerializer,
    RetrieveRelaseSerializer,
)


@extend_schema(tags=["project"])
class ProjectView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProjectModel.objects.all()
        if self.request.user.is_authenticated:
            return queryset.filter(owner=self.request.user)
        return queryset.none()

    def perform_create(self, serializer):
        flow = FlowModel.objects.create(
            flow={
                "nodes": [],
                "edges": []
            }
        )
        return serializer.save(owner=self.request.user, flow=flow)

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
        "partial_update": CreateProjectSerializer
    }


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


@extend_schema(tags=["flow"])
class FlowView(BaseViewSetMixin, ModelViewSet):
    queryset = FlowModel.objects.all()
    serializer_class = ListFlowSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListFlowSerializer,
        "retrieve": RetrieveFlowSerializer,
        "create": CreateFlowSerializer,
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
