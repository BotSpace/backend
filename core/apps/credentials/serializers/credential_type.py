from __future__ import annotations

from rest_framework import serializers

from core.apps.credentials.models import CredentialType


class CredentialTypeSerializer(serializers.ModelSerializer):
    """Read/write serializer for CredentialType.

    system=True types cannot be edited or deleted via the API (enforced at view level).
    """

    class Meta:
        model = CredentialType
        fields = [
            "id",
            "key",
            "label",
            "description",
            "icon",
            "mode",
            "fields",
            "system",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "system", "owner", "created_at", "updated_at"]

    def validate_fields(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("fields must be a list")
        valid_types = {"text", "password", "number", "select", "textarea"}
        for idx, field in enumerate(value):
            if not isinstance(field, dict):
                raise serializers.ValidationError(f"fields[{idx}] must be an object")
            if not field.get("name"):
                raise serializers.ValidationError(f"fields[{idx}].name is required")
            if field.get("type") and field["type"] not in valid_types:
                raise serializers.ValidationError(
                    f"fields[{idx}].type must be one of {valid_types}"
                )
            if field.get("type") == "select" and not field.get("options"):
                raise serializers.ValidationError(f"fields[{idx}].options required for select type")
        return value
