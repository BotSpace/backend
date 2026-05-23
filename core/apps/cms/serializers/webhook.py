from rest_framework import serializers

from core.apps.cms.models import Webhook


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = [
            "id",
            "name",
            "url",
            "event",
            "secret",
            "headers",
            "active",
            "last_status",
            "last_fired_at",
            "failure_count",
            "created_at",
        ]
        read_only_fields = ["id", "last_status", "last_fired_at", "failure_count", "created_at"]
