"""/api/v1/credentials/ — Owner-scoped Credential CRUD (v2)."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.apps.credentials.models import Credential
from core.apps.credentials.serializers import (
    CredentialCreateSerializer,
    CredentialDetailSerializer,
    CredentialListSerializer,
    CredentialPatchSerializer,
)


@extend_schema(tags=["credentials"])
class CredentialViewSet(ViewSet):
    """Owner-scoped credential CRUD — request.user scope, no project in path."""

    permission_classes = [IsAuthenticated]

    def _get_qs(self):
        qs = Credential.objects.filter(owner=self.request.user, deleted_at__isnull=True)
        type_key = self.request.query_params.get("type_key")
        if type_key:
            qs = qs.filter(type_key=type_key)
        return qs.order_by("name")

    def _get_object(self, pk):
        cred = self._get_qs().filter(pk=pk).first()
        if cred is None:
            raise NotFound("Credential not found")
        return cred

    def list(self, request):
        qs = self._get_qs()
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("page_size", 20))
        paginator.max_page_size = 100
        page = paginator.paginate_queryset(qs, request)
        serializer = CredentialListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        serializer = CredentialCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        credential = serializer.save()
        return Response(
            CredentialDetailSerializer(credential).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        cred = self._get_object(pk)
        return Response(CredentialDetailSerializer(cred).data)

    def partial_update(self, request, pk=None):
        cred = self._get_object(pk)
        serializer = CredentialPatchSerializer(cred, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(CredentialDetailSerializer(updated).data)

    def destroy(self, request, pk=None):
        cred = self._get_object(pk)
        cred.deleted_at = timezone.now()
        cred.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="test")
    def test_credential(self, request, pk=None):
        """Stub endpoint — always returns ok:true."""
        self._get_object(pk)
        return Response({"ok": True})
