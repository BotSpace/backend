# type: ignore
"""Serializers for SettingsModel / OptionsModel admin endpoints."""

from rest_framework import serializers

from core.apps.shared.models.settings import OptionsModel, SettingsModel


class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionsModel
        fields = ("key", "value")


class AdminSettingsSerializer(serializers.ModelSerializer):
    options = AdminOptionSerializer(many=True, read_only=True)

    class Meta:
        model = SettingsModel
        fields = ("key", "description", "is_public", "options")


class AdminSettingsSetSerializer(serializers.Serializer):
    settings_key = serializers.CharField(max_length=255)
    option_key = serializers.CharField(max_length=255)
    value = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
    )

    def validate_value(self, value):
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each element must be a string.")
        return value
