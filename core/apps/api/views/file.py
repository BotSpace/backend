from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
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
    queryset = FileModel.objects.all()
    serializer_class = ListFileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListFileSerializer,
        "retrieve": RetrieveFileSerializer,
        "create": CreateFileSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
