"""Credential serializers — v2 owner-scoped, registry-based types, secret masking."""
from __future__ import annotations

from rest_framework import serializers

from core.apps.credentials.models import Credential
from core.apps.credentials.registry import get_type, list_types
from core.apps.credentials.services import crypto


def _mask(value: str) -> str:
    """Return ••••<last4> or None if value is too short."""
    if not value or len(str(value)) <= 4:
        return None
    return "••••" + str(value)[-4:]


def _mask_data(fields_schema: list, data: dict, mode: str = "") -> dict:
    """Return data dict with secret fields masked.

    For oauth2 credentials (empty fields_schema), mask access_token and refresh_token
    but surface account_email and scope as non-secret info.
    """
    if mode == "oauth2":
        # Tokens are always secret; account_email and scope are surfaced plaintext
        secret_keys = {"access_token", "refresh_token"}
        result = {}
        for key, val in data.items():
            if key in secret_keys:
                result[key] = _mask(str(val)) if val else None
            else:
                result[key] = val
        return result

    secret_names = {f["name"] for f in fields_schema if f.get("secret")}
    result = {}
    for key, val in data.items():
        if key in secret_names:
            result[key] = _mask(str(val)) if val else None
        else:
            result[key] = val
    return result


def _validate_data_against_fields(fields_schema: list, data: dict):
    """Validate data dict against a list of field descriptors. Raises ValidationError on failure."""
    errors = []
    for field in fields_schema:
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


class CredentialRegistryTypeSerializer(serializers.Serializer):
    """Read-only serializer for a single registry type entry."""
    key = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField(required=False, allow_null=True, default=None)
    mode = serializers.CharField()
    fields = serializers.ListField()
    provider = serializers.CharField(required=False, allow_null=True, default=None)
    scopes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    source = serializers.CharField(required=False, default="code")
    editable = serializers.BooleanField(required=False, default=False)


class CredentialListSerializer(serializers.ModelSerializer):
    """List/detail output — includes type info from registry + masked data."""

    type_key = serializers.CharField(read_only=True)
    type = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    mode = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = [
            "id",
            "name",
            "type_key",
            "type",
            "label",
            "mode",
            "data",
            "created_at",
            "updated_at",
        ]

    def _type_info(self, obj: Credential) -> dict:
        return get_type(obj.type_key) or {}

    def get_type(self, obj: Credential) -> dict:
        info = get_type(obj.type_key)
        if info is None:
            return {"key": obj.type_key, "label": obj.type_key, "mode": "none"}
        return {
            "key": obj.type_key,
            "label": info.get("label"),
            "mode": info.get("mode"),
        }

    def _decrypted(self, obj: Credential) -> dict:
        try:
            return crypto.decrypt(obj.data_encrypted)
        except Exception:
            return {}

    def get_label(self, obj: Credential) -> str | None:
        return self._type_info(obj).get("label")

    def get_mode(self, obj: Credential) -> str | None:
        return self._type_info(obj).get("mode")

    def get_data(self, obj: Credential) -> dict:
        info = self._type_info(obj)
        fields_schema = info.get("fields", [])
        mode = info.get("mode", "")
        raw = self._decrypted(obj)
        return _mask_data(fields_schema, raw, mode=mode)


class CredentialDetailSerializer(CredentialListSerializer):
    """Same as list but includes owner id."""

    class Meta(CredentialListSerializer.Meta):
        fields = CredentialListSerializer.Meta.fields + ["owner"]


class CredentialCreateSerializer(serializers.Serializer):
    """POST — create a new credential."""

    type_key = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=120)
    data = serializers.JSONField()

    def validate_type_key(self, value: str) -> str:
        if get_type(value) is None:
            valid_keys = [t["key"] for t in list_types()]
            raise serializers.ValidationError(
                f"Unknown type_key '{value}'. Valid: {valid_keys}"
            )
        return value

    def validate(self, attrs):
        type_key = attrs.get("type_key")
        data = attrs.get("data", {})
        if type_key:
            info = get_type(type_key)
            if info:
                # oauth2 types have empty fields — skip field validation (tokens come from callback)
                if info.get("mode") != "oauth2":
                    _validate_data_against_fields(info["fields"], data)
        return attrs

    def create(self, validated_data):
        owner = self.context["request"].user
        data = validated_data.pop("data")
        return Credential.objects.create(
            owner=owner,
            data_encrypted=crypto.encrypt(data),
            **validated_data,
        )


class CredentialPatchSerializer(serializers.Serializer):
    """PATCH — partial update; empty/omitted secret fields keep old value."""

    name = serializers.CharField(max_length=120, required=False)
    data = serializers.JSONField(required=False)

    def validate(self, attrs):
        if "data" in attrs:
            instance: Credential = self.instance
            info = get_type(instance.type_key) or {}
            fields_schema = info.get("fields", [])
            mode = info.get("mode", "")
            try:
                old_data = crypto.decrypt(instance.data_encrypted)
            except Exception:
                old_data = {}

            new_data = attrs["data"]

            if mode == "oauth2":
                # oauth2: merge new into old (e.g. manual token update), no field schema validation
                merged = dict(old_data)
                merged.update(new_data)
                attrs["data"] = merged
            else:
                secret_names = {f["name"] for f in fields_schema if f.get("secret")}

                # Merge: secret field empty or absent => keep old value
                merged = dict(old_data)
                for key, val in new_data.items():
                    if key in secret_names and (val is None or val == ""):
                        pass  # keep old
                    else:
                        merged[key] = val

                _validate_data_against_fields(fields_schema, merged)
                attrs["data"] = merged
        return attrs

    def update(self, instance: Credential, validated_data: dict):
        if "name" in validated_data:
            instance.name = validated_data["name"]
        if "data" in validated_data:
            instance.data_encrypted = crypto.encrypt(validated_data["data"])
        instance.save(update_fields=["name", "data_encrypted", "updated_at"])
        return instance
