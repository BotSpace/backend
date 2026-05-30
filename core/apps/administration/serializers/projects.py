# type: ignore
from rest_framework import serializers

from core.apps.api.models.project import ProjectModel


class AdminProjectSerializer(serializers.ModelSerializer):
    owner_phone = serializers.CharField(source="owner.phone", read_only=True)
    owner_id = serializers.IntegerField(source="owner_id", read_only=True)

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
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
