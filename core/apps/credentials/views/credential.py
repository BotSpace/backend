"""/api/v1/credentials/projects/<project_id>/credentials/ — Credential CRUD."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.apps.credentials.models import Credential
from core.apps.credentials.serializers import (
    CredentialCreateSerializer,
    CredentialDetailSerializer,
    CredentialListSerializer,
)
from core.apps.credentials.serializers.credential import CredentialPatchSerializer

from ._common import get_project_or_404


@extend_schema(tags=["credentials"])
class CredentialViewSet(ViewSet):
    """Project-scoped credential CRUD."""

    permission_classes = [IsAuthenticated]

    def _get_project(self, project_id):
        return get_project_or_404(project_id, user=self.request.user)

    def _get_qs(self, project):
        qs = Credential.objects.filter(project=project, deleted_at__isnull=True).select_related("type")
        # Filter by type key
        type_key = self.request.query_params.get("type")
        if type_key:
            qs = qs.filter(type__key=type_key)
        return qs.order_by("name")

    def list(self, request, project_id=None):
        project = self._get_project(project_id)
        qs = self._get_qs(project)

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("page_size", 20))
        paginator.max_page_size = 100
        page = paginator.paginate_queryset(qs, request)
        serializer = CredentialListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def create(self, request, project_id=None):
        project = self._get_project(project_id)
        serializer = CredentialCreateSerializer(
            data=request.data,
            context={"request": request, "project": project},
        )
        serializer.is_valid(raise_exception=True)
        credential = serializer.save()
        return Response(
            CredentialDetailSerializer(credential, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, project_id=None, pk=None):
        project = self._get_project(project_id)
        cred = self._get_qs(project).filter(pk=pk).first()
        if cred is None:
            raise NotFound("Credential not found")
        return Response(CredentialDetailSerializer(cred, context={"request": request}).data)

    def partial_update(self, request, project_id=None, pk=None):
        project = self._get_project(project_id)
        cred = self._get_qs(project).filter(pk=pk).first()
        if cred is None:
            raise NotFound("Credential not found")
        serializer = CredentialPatchSerializer(
            cred,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(CredentialDetailSerializer(updated, context={"request": request}).data)

    def destroy(self, request, project_id=None, pk=None):
        project = self._get_project(project_id)
        cred = self._get_qs(project).filter(pk=pk).first()
        if cred is None:
            raise NotFound("Credential not found")
        cred.deleted_at = timezone.now()
        cred.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="test")
    def test_credential(self, request, project_id=None, pk=None):
        """Stub endpoint — always returns ok:true."""
        project = self._get_project(project_id)
        cred = self._get_qs(project).filter(pk=pk).first()
        if cred is None:
            raise NotFound("Credential not found")
        return Response({"ok": True})
