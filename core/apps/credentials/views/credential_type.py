"""/api/v1/credentials/types/ — CredentialType CRUD."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.apps.credentials.models import CredentialType
from core.apps.credentials.serializers import CredentialTypeSerializer


@extend_schema(tags=["credentials"])
class CredentialTypeViewSet(ModelViewSet):
    """List/create/retrieve/update/delete CredentialTypes.

    System types (system=True) cannot be updated or deleted.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CredentialTypeSerializer
    lookup_field = "key"

    def get_queryset(self):
        # System types + types owned by current user
        user = self.request.user
        from django.db.models import Q
        return CredentialType.objects.filter(
            Q(system=True) | Q(owner=user)
        ).order_by("key")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _check_not_system(self, instance: CredentialType):
        if instance.system:
            raise PermissionDenied("System credential types cannot be modified or deleted.")

    def perform_update(self, serializer):
        self._check_not_system(self.get_object())
        serializer.save()

    def perform_destroy(self, instance: CredentialType):
        self._check_not_system(instance)
        instance.delete()

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
