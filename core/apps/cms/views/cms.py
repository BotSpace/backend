from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.apps.cms.models import CollectionModel
from core.apps.cms.serializers.cms import (
    CreateCollectionSerializer,
    ListCollectionSerializer,
    RetrieveCollectionSerializer,
)


@extend_schema(tags=["collection"])
class CollectionView(BaseViewSetMixin, ModelViewSet):
    queryset = CollectionModel.objects.all()
    serializer_class = ListCollectionSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListCollectionSerializer,
        "retrieve": RetrieveCollectionSerializer,
        "create": CreateCollectionSerializer,
        "update": CreateCollectionSerializer,
        "partial_update": CreateCollectionSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
