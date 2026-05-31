from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
)

from core.apps.api.models import FileModel
from core.apps.api.serializers.file import CreateFileSerializer, ListFileSerializer, RetrieveFileSerializer


@extend_schema(tags=["file"])
class FileView(
    BaseViewSetMixin,
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = ListFileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "filetype",
    ]

    action_permission_classes = {
        "retrieve": [AllowAny],
    }
    action_serializer_class = {
        "list": ListFileSerializer,
        "retrieve": RetrieveFileSerializer,
        "create": CreateFileSerializer,
    }

    def get_queryset(self):
        if self.action == "retrieve":
            return FileModel.objects.all()
        qs = FileModel.objects.filter(user=self.request.user)
        project_raw = self.request.query_params.get("project")
        if project_raw:
            from core.apps.cms.views._common import resolve_project

            project = resolve_project(project_raw)
            qs = qs.filter(project_id=project.pk) if project else qs.none()
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
