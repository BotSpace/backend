from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models import BotModel, ProjectModel
from core.apps.api.serializers.project import (
    CreateBotSerializer,
    CreateProjectSerializer,
    ListBotSerializer,
    ListProjectSerializer,
    RetrieveBotSerializer,
    RetrieveProjectSerializer,
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
        return serializer.save(owner=self.request.user)

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListProjectSerializer,
        "retrieve": RetrieveProjectSerializer,
        "create": CreateProjectSerializer,
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
