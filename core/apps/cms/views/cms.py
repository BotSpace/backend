# type: ignore
import json
import logging
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from bson import json_util

from core.apps.cms.models import CollectionModel
from core.apps.cms.serializers.cms import (
    CreateCollectionSerializer,
    ListCollectionSerializer,
    RetrieveCollectionSerializer,
)
from core.apps.cms.serializers.cms.collection import (
    AddDataCollectionSerializer,
    CountDataCollectionSerializer,
    DeleteDataCollectionSerializer,
    FindDataCollectionSerializer,
    FindOneDataCollectionSerializer,
    InsertIfNotExists,
    UpdateCollectionSerializer,
    UpdateDataCollectionSerializer,
)
from core.apps.cms.services.action import ActionService
from core.apps.cms.services.collection import collection_validate_data
from core.apps.cms.services.mongo import (
    count_document,
    delete,
    find,
    find_one,
    get_collection_name,
    insert_if_not_exists,
    insert_one,
    update,
)


@extend_schema(tags=["collection"])
class CollectionView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListCollectionSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListCollectionSerializer,
        "retrieve": RetrieveCollectionSerializer,
        "create": CreateCollectionSerializer,
        "update": UpdateCollectionSerializer,
        "partial_update": UpdateCollectionSerializer,
    }

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        return get_object_or_404(queryset, name=self.kwargs["pk"])

    def get_queryset(self):
        queryset = CollectionModel.objects.filter(user=self.request.user)
        project = self.request.query_params.get("project")
        if project is None:
            raise ValidationError(detail={"project": ["project query_params is required"]})
        return queryset.filter(project=project)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(methods=["POST"], detail=True, url_name="query", url_path="query")
    def query(self, request, pk):
        instance = self.get_object()
        action_seriazlier = {
            "find": FindDataCollectionSerializer,
            "find_one": FindOneDataCollectionSerializer,
            "count": CountDataCollectionSerializer,
            "update": UpdateDataCollectionSerializer,
            "insert": AddDataCollectionSerializer,
            "insert_if_not_exists": InsertIfNotExists,
            "delete": DeleteDataCollectionSerializer,
        }
        action = request.query_params.get("action")
        context = {"request": request, "collection": instance}
        if action is None:
            raise ValidationError(detail={"action": ["action query_params is required"]})
        if action not in action_seriazlier:
            raise ValidationError(detail={"action": ["invalid action"]})

        ser = action_seriazlier.get(action)(context=context, data=request.data)
        ser.is_valid(raise_exception=True)
        action_service = ActionService(instance, ser.validated_data)
        actions = {
            "insert": action_service.insert,
            "delete": action_service.delete,
            "insert_if_not_exists": action_service.insert_if_not_exists,
            "update": action_service.update,
            "find": action_service.find,
            "find_one": action_service.find_one,
            "count": action_service.count,
        }
        try:
            action_handler = actions.get(action, None)
            if action_handler is None:
                raise ValidationError(detail={"action": ["Invalid action"]})
            response, status_code = action_handler()
            return Response(data=response, status=status_code)
        except Exception as e:
            logging.exception(
                "Collection data %s error: %s" % (action, str(e)),
            )
            return Response(data={"detail": str(e)}, status=500)
