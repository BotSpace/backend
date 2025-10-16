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

from config import env
from core.apps.cms.models import CollectionModel
from core.apps.cms.serializers.cms import (
    CreateCollectionSerializer,
    ListCollectionSerializer,
    RetrieveCollectionSerializer,
)
from core.apps.cms.serializers.cms.collection import (
    AddDataCollectionSerializer,
    DeleteDataCollectionSerializer,
    FindDataCollectionSerializer,
    FindOneDataCollectionSerializer,
    UpdateCollectionSerializer,
    UpdateDataCollectionSerializer,
)
from core.apps.cms.services.collection import collection_validate_data
from core.apps.cms.services.mongo import delete, find, find_one, get_collection_name, insert_one, update


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
        "update": UpdateCollectionSerializer,
        "partial_update": UpdateCollectionSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(methods=["POST"], detail=True, url_name="query", url_path="query")
    def query(self, request, pk):
        instance = get_object_or_404(CollectionModel, pk=pk)
        action_seriazlier = {
            "find": FindDataCollectionSerializer,
            "find_one": FindOneDataCollectionSerializer,
            "update": UpdateDataCollectionSerializer,
            "insert": AddDataCollectionSerializer,
            "delete": DeleteDataCollectionSerializer,
        }
        action = request.query_params.get("action")
        context = {"request": request}
        collection_name = get_collection_name(instance)
        if action is None:
            raise ValidationError(detail={"action": "action query_params is required"})
        if action not in action_seriazlier:
            raise ValidationError(detail={"action": "invalid action"})

        ser = action_seriazlier.get(action)(context=context, data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            if action == "insert":
                errors, success = collection_validate_data(instance, ser.validated_data)
                if not success:
                    return Response(data=errors, status=400)
                inserted_id = insert_one(collection_name, ser.validated_data)
                return Response(data={"inserted_id": str(inserted_id)})
            elif action == "find":
                data = find(
                    collection_name,
                    where=ser.validated_data.get("where", {}),
                    limit=ser.validated_data.get("limit", None),
                    _sort=ser.validated_data.get("sort", None),
                    skip=ser.validated_data.get("skip", None),
                )
                return Response(data=json.loads(json_util.dumps(data)))
            elif action == "find_one":
                data = find_one(collection_name, where=ser.validated_data.get("where", {}))
                if data is None:
                    return Response(data={"detail": "Not found"}, status=404)
                return Response(data=json.loads(json_util.dumps(data)))
            elif action == "update":
                res = update(collection_name, ser.validated_data.get("where", {}), ser.validated_data.get("data"))
                return Response(data={"modified_count": res.modified_count})
            elif action == "delete":
                res = delete(collection_name, ser.validated_data.get("where", {}))
                return Response(data={"deleted_count": res.deleted_count})
            raise ValidationError(detail={"action": "Invalid action"})
        except Exception as e:
            logging.exception(
                "Collection data %s error: %s" % (action, str(e)),
            )
            return Response(
                data={
                    "detail": str(e),
                }
            )
