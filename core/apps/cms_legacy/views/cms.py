# type: ignore
import logging
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status

from core.apps.cms_legacy.models import CollectionModel, ExportTaskModel
from core.apps.cms_legacy.serializers.cms import (
    CreateCollectionSerializer,
    ListCollectionSerializer,
    RetrieveCollectionSerializer,
    ExportCollectionSerializer,
    ExportTaskStatusSerializer,
)
from core.apps.cms_legacy.serializers.cms.collection import (
    AddDataCollectionSerializer,
    CountDataCollectionSerializer,
    DeleteDataCollectionSerializer,
    FindDataCollectionSerializer,
    FindOneDataCollectionSerializer,
    InsertIfNotExists,
    UpdateCollectionSerializer,
    UpdateDataCollectionSerializer,
)
from core.apps.cms_legacy.services.action import ActionService
from core.apps.cms_legacy.tasks import export_collection_to_excel


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
        "export_excel": ExportCollectionSerializer,
        "export_status": ExportTaskStatusSerializer,
    }

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        return get_object_or_404(queryset, name=self.kwargs["pk"])

    def get_queryset(self):
        queryset = CollectionModel.objects.filter(user=self.request.user)
        if self.action in ["export_excel", "export_status"]:
            return queryset
        project = self.request.query_params.get("project")
        if project is None:
            raise ValidationError(detail={"project": ["project query_params is required"]})
        return queryset.filter(project=project)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if not instance.can_delete:
            raise ValidationError(detail={"detail": "bu collectionni o'chirish mumkun emas!!!"})
        instance.delete()

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

    @extend_schema(
        responses={
            202: ExportTaskStatusSerializer,
        }
    )
    @action(methods=["POST"], detail=True, url_name="export-excel", url_path="export-excel")
    def export_excel(self, request, pk):
        """
        Initiate Excel export for collection data.
        Returns task_id to track export progress.
        """
        instance = self.get_object()

        # Create export task
        export_task = ExportTaskModel.objects.create(collection=instance, status=ExportTaskModel.Status.PENDING)

        # Start Celery task
        export_collection_to_excel.delay(str(export_task.task_id))

        serializer = ExportTaskStatusSerializer(export_task, context={"request": request})
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(methods=["GET"], detail=False, url_name="export-status", url_path="export-status/(?P<task_id>[^/.]+)")
    def export_status(self, request, task_id=None, pk=None):
        """
        Check status of export task by task_id.
        """
        try:
            export_task = ExportTaskModel.objects.get(task_id=task_id)

            # Check if user has access to this collection
            if export_task.collection.user != request.user:
                raise PermissionDenied("You do not have permission to access this export.")

            serializer = ExportTaskStatusSerializer(export_task, context={"request": request})
            return Response(serializer.data)

        except ExportTaskModel.DoesNotExist:
            return Response({"detail": "Export task not found."}, status=status.HTTP_404_NOT_FOUND)
