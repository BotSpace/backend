"""/api/v1/credentials/types/ — Read-only registry endpoint (v2)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.credentials.registry import list_types
from core.apps.credentials.serializers import CredentialRegistryTypeSerializer


@extend_schema(tags=["credentials"])
class CredentialTypeListView(APIView):
    """Return the full read-only credential type registry."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        types = list_types()
        serializer = CredentialRegistryTypeSerializer(types, many=True)
        return Response(serializer.data)
