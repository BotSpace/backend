from rest_framework import serializers

from core.apps.cms.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(source="actor.id", read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "actor_id",
            "document_id",
            "before",
            "after",
            "meta",
            "created_at",
        ]
        read_only_fields = fields
