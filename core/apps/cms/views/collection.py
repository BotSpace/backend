"""/api/v1/cms/projects/{project_id}/collections/* — schema CRUD."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.apps.cms.enums import AuditAction
from core.apps.cms.models import Collection, Field
from core.apps.cms.serializers import (
    CollectionCreateSerializer,
    CollectionDetailSerializer,
    CollectionListSerializer,
    FieldSerializer,
)
from core.apps.cms.services import audit, schema as schema_svc

from ._common import get_project_or_404


@extend_schema(tags=["cms"])
class CollectionViewSet(ModelViewSet):
    """Per-project collection (schema) CRUD."""

    permission_classes = [IsAuthenticated]
    lookup_field = "name"
    lookup_url_kwarg = "name"

    def get_queryset(self):
        project = get_project_or_404(self.kwargs["project_id"], user=self.request.user)
        return (
            Collection.objects.filter(project_id=project.pk, deleted_at__isnull=True)
            .prefetch_related("fields")
            .order_by("name")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionListSerializer
        if self.action == "create":
            return CollectionCreateSerializer
        return CollectionDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["project"] = get_project_or_404(self.kwargs["project_id"], user=self.request.user)
        return ctx

    def perform_create(self, serializer):
        coll: Collection = serializer.save()
        audit.log(
            coll,
            self.request.user.id if self.request.user.is_authenticated else None,
            AuditAction.SCHEMA_CREATE,
            after=schema_svc.schema_dict_for(coll),
        )

    def perform_destroy(self, instance: Collection):
        if not instance.can_delete:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("System collection cannot be deleted")
        from django.utils import timezone

        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        audit.log(
            instance,
            self.request.user.id if self.request.user.is_authenticated else None,
            AuditAction.SCHEMA_DELETE,
        )

    # ── extra: add field ───────────────────────────────────────────────
    @action(detail=True, methods=["post"], url_path="fields")
    def add_field(self, request, project_id=None, name=None):
        coll = self.get_object()
        ser = FieldSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        field = Field.objects.create(collection=coll, **ser.validated_data)
        audit.log(
            coll,
            request.user.id if request.user.is_authenticated else None,
            AuditAction.SCHEMA_UPDATE,
            meta={"field_added": field.name},
        )
        return Response(FieldSerializer(field).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path=r"fields/(?P<field_name>[^/.]+)")
    def update_field(self, request, project_id=None, name=None, field_name=None):
        coll = self.get_object()
        field = coll.fields.filter(name=field_name).first()
        if field is None:
            return Response({"detail": "Field not found"}, status=404)
        ser = FieldSerializer(field, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        audit.log(
            coll,
            request.user.id if request.user.is_authenticated else None,
            AuditAction.SCHEMA_UPDATE,
            meta={"field_updated": field_name},
        )
        return Response(ser.data)

    @action(detail=True, methods=["delete"], url_path=r"fields/(?P<field_name>[^/.]+)")
    def remove_field(self, request, project_id=None, name=None, field_name=None):
        coll = self.get_object()
        field = coll.fields.filter(name=field_name).first()
        if field is None:
            return Response({"detail": "Field not found"}, status=404)
        field.delete()
        audit.log(
            coll,
            request.user.id if request.user.is_authenticated else None,
            AuditAction.SCHEMA_UPDATE,
            meta={"field_removed": field_name},
        )
        return Response(status=204)
