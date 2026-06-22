"""/api/v1/credentials/types/ — Read (all users) + Admin CRUD (staff only)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.credentials.registry import (
    VALID_FIELD_TYPES,
    VALID_MODES,
    admin_create_type,
    admin_delete_type,
    admin_update_type,
    get_type,
    list_types,
)
from core.apps.credentials.serializers import CredentialRegistryTypeSerializer
from core.permissions.engine import IsAdminUser


# ---------------------------------------------------------------------------
# Input serializers (admin write)
# ---------------------------------------------------------------------------

class _FieldSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    label = serializers.CharField(max_length=120)
    type = serializers.ChoiceField(choices=list(VALID_FIELD_TYPES))
    secret = serializers.BooleanField(required=False, default=False)
    required = serializers.BooleanField(required=False, default=False)
    default = serializers.JSONField(required=False, default=None, allow_null=True)
    options = serializers.ListField(required=False, default=list)  # [{label, value}]


class AdminCredentialTypeCreateSerializer(serializers.Serializer):
    key = serializers.RegexField(r'^[a-z][a-z0-9_]{1,49}$', max_length=50)
    label = serializers.CharField(max_length=120)
    icon = serializers.CharField(max_length=80, required=False, default="key")
    color = serializers.CharField(max_length=20, required=False, default="#6B7280")
    mode = serializers.ChoiceField(choices=list(VALID_MODES))
    fields = _FieldSerializer(many=True, required=False, default=list)


class AdminCredentialTypePatchSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120, required=False)
    icon = serializers.CharField(max_length=80, required=False)
    color = serializers.CharField(max_length=20, required=False)
    mode = serializers.ChoiceField(choices=list(VALID_MODES), required=False)
    fields = _FieldSerializer(many=True, required=False)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@extend_schema(tags=["credentials"])
class CredentialTypeListView(APIView):
    """
    GET  — all authenticated users; returns types from code + admin + module sources.
    POST — staff/admin only; create an admin-managed credential type.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get(self, request):
        types = list_types(request=request)
        serializer = CredentialRegistryTypeSerializer(types, many=True)
        return Response(serializer.data)

    def post(self, request):
        ser = AdminCredentialTypeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        # Normalize fields to plain dicts (OrderedDict from serializer)
        data["fields"] = [dict(f) for f in data.get("fields", [])]
        try:
            created = admin_create_type(data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = dict(created, source="admin", editable=True)
        return Response(CredentialRegistryTypeSerializer(out).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["credentials"])
class CredentialTypeDetailView(APIView):
    """
    PATCH  — staff/admin only; update an admin type.
    DELETE — staff/admin only; delete an admin type.
    Only types with source=admin are mutable (code/module types return 403).
    """

    permission_classes = [IsAdminUser]

    def _get_admin_or_403(self, key: str):
        """Return the type dict if it is an admin type, else raise."""
        existing = get_type(key)
        if existing is None:
            return None, Response({"detail": f"Type '{key}' not found."}, status=status.HTTP_404_NOT_FOUND)
        # Check if it is an admin type by looking it up in the admin list
        from core.apps.credentials.registry import _get_admin_types
        admin_keys = {t.get("key") for t in _get_admin_types()}
        if key not in admin_keys:
            return None, Response(
                {"detail": "Only admin-created types can be modified."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return existing, None

    def patch(self, request, key: str):
        existing, err = self._get_admin_or_403(key)
        if err:
            return err
        ser = AdminCredentialTypePatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        patch = ser.validated_data
        if "fields" in patch:
            patch["fields"] = [dict(f) for f in patch["fields"]]
        try:
            updated = admin_update_type(key, patch)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = dict(updated, source="admin", editable=True)
        return Response(CredentialRegistryTypeSerializer(out).data)

    def delete(self, request, key: str):
        _existing, err = self._get_admin_or_403(key)
        if err:
            return err
        try:
            admin_delete_type(key)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
