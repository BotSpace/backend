from rest_framework import serializers

from core.apps.shared.models import Config


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = ["key", "value", "label", "group", "is_public", "description"]
        read_only_fields = ["key"]


class ConfigUpdateSerializer(serializers.ModelSerializer):
    """Used by admin PATCH — only value is writable."""

    class Meta:
        model = Config
        fields = ["key", "value", "label", "group", "is_public", "description"]
        read_only_fields = ["key"]
