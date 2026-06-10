# type: ignore
from rest_framework import serializers

from core.apps.api.models.project import ProjectModel


class AdminProjectSerializer(serializers.ModelSerializer):
    # owner_id is a real model field (FK id), so ModelSerializer exposes it
    # automatically — no explicit declaration needed.
    owner_phone = serializers.CharField(source="owner.phone", read_only=True)
    # Oxirgi relizning holati (running/active/stopped/...) — queryset'da Subquery
    # bilan annotate qilinadi. Reliz yo'q bo'lsa None.
    release_status = serializers.CharField(source="latest_release_status", read_only=True)

    class Meta:
        model = ProjectModel
        fields = (
            "id",
            "name",
            "description",
            "username",
            "owner_id",
            "owner_phone",
            "is_template",
            "release_webhook_uuid",
            "release_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
