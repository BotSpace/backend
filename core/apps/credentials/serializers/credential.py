"""Credential serializers with secret masking and PATCH merge logic."""
from __future__ import annotations

from rest_framework import serializers

from core.apps.credentials.models import Credential, CredentialType
from core.apps.credentials.services import crypto


def _mask(value: str) -> str:
    """Return ••••<last4> or None if value is too short."""
    if not value or len(str(value)) <= 4:
        return None
    return "••••" + str(value)[-4:]


def _mask_data(fields_schema: list, data: dict) -> dict:
    """Return data dict with secret fields masked."""
    secret_names = {f["name"] for f in fields_schema if f.get("secret")}
    result = {}
    for key, val in data.items():
        if key in secret_names:
            result[key] = _mask(str(val)) if val else None
        else:
            result[key] = val
    return result


class CredentialTypeInlineSerializer(serializers.Serializer):
    """Minimal type representation embedded in credential responses."""
    id = serializers.IntegerField(read_only=True)
    key = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    mode = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True)
    fields = serializers.JSONField(read_only=True)


class CredentialListSerializer(serializers.ModelSerializer):
    type = CredentialTypeInlineSerializer(read_only=True)
    data = serializers.SerializerMethodField()
    data_keys = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = [
            "id",
            "name",
            "type",
            "data",
            "data_keys",
            "created_at",
            "updated_at",
        ]

    def _decrypted(self, obj: Credential) -> dict:
        try:
            return crypto.decrypt(obj.data_encrypted)
        except Exception:
            return {}

    def get_data(self, obj: Credential) -> dict:
        raw = self._decrypted(obj)
        return _mask_data(obj.type.fields, raw)

    def get_data_keys(self, obj: Credential) -> list:
        return list(self._decrypted(obj).keys())


class CredentialDetailSerializer(CredentialListSerializer):
    class Meta(CredentialListSerializer.Meta):
        fields = CredentialListSerializer.Meta.fields + ["project", "owner"]


class CredentialCreateSerializer(serializers.ModelSerializer):
    """Used for POST (create) — accepts raw data, validates against type.fields."""

    type_id = serializers.PrimaryKeyRelatedField(
        queryset=CredentialType.objects.all(), source="type", write_only=True
    )
    data = serializers.JSONField(write_only=True)

    class Meta:
        model = Credential
        fields = ["id", "name", "type_id", "data"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        ctype: CredentialType = attrs["type"]
        data: dict = attrs.get("data", {})
        self._validate_data_against_type(ctype, data)
        return attrs

    def _validate_data_against_type(self, ctype: CredentialType, data: dict):
        errors = []
        for field in ctype.fields:
            name = field.get("name")
            required = field.get("required", False)
            ftype = field.get("type", "text")
            options = field.get("options", [])

            val = data.get(name)
            if required and (val is None or val == ""):
                errors.append(f"{name}: required")
                continue
            if val is not None and ftype == "select" and options:
                valid_values = [o["value"] for o in options if isinstance(o, dict)]
                if val not in valid_values:
                    errors.append(f"{name}: must be one of {valid_values}")
        if errors:
            raise serializers.ValidationError({"data": errors})

    def create(self, validated_data):
        data = validated_data.pop("data")
        project = self.context["project"]
        owner = self.context["request"].user
        owner = owner if (owner and owner.is_authenticated) else None
        return Credential.objects.create(
            project=project,
            owner=owner,
            data_encrypted=crypto.encrypt(data),
            **validated_data,
        )


class CredentialPatchSerializer(serializers.ModelSerializer):
    """Used for PATCH — merges secret fields (empty/omitted => keep old value)."""

    data = serializers.JSONField(required=False)

    class Meta:
        model = Credential
        fields = ["name", "data"]

    def validate(self, attrs):
        if "data" in attrs:
            ctype: CredentialType = self.instance.type
            try:
                old_data = crypto.decrypt(self.instance.data_encrypted)
            except Exception:
                old_data = {}

            new_data = attrs["data"]
            secret_names = {f["name"] for f in ctype.fields if f.get("secret")}

            # Merge: secret field empty or absent => keep old value
            merged = dict(old_data)
            for key, val in new_data.items():
                if key in secret_names and (val is None or val == ""):
                    pass  # keep old
                else:
                    merged[key] = val

            # Validate non-empty data against type
            self._validate_data_against_type(ctype, merged)
            attrs["data"] = merged
        return attrs

    def _validate_data_against_type(self, ctype: CredentialType, data: dict):
        errors = []
        for field in ctype.fields:
            name = field.get("name")
            required = field.get("required", False)
            ftype = field.get("type", "text")
            options = field.get("options", [])

            val = data.get(name)
            if required and (val is None or val == ""):
                errors.append(f"{name}: required")
                continue
            if val is not None and ftype == "select" and options:
                valid_values = [o["value"] for o in options if isinstance(o, dict)]
                if val not in valid_values:
                    errors.append(f"{name}: must be one of {valid_values}")
        if errors:
            raise serializers.ValidationError({"data": errors})

    def update(self, instance: Credential, validated_data: dict):
        if "name" in validated_data:
            instance.name = validated_data["name"]
        if "data" in validated_data:
            instance.data_encrypted = crypto.encrypt(validated_data["data"])
        instance.save(update_fields=["name", "data_encrypted", "updated_at"])
        return instance
