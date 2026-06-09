from rest_framework import serializers

from core.apps.tickets.models.ticket import TicketModel


class TicketSerializer(serializers.ModelSerializer):
    """Foydalanuvchiga o'z murojaatini ko'rsatish uchun."""

    class Meta:
        model = TicketModel
        fields = [
            "id",
            "subject",
            "message",
            "status",
            "admin_reply",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "admin_reply", "created_at", "updated_at"]


class CreateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketModel
        fields = ["subject", "message"]

    def validate_subject(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Mavzu bo'sh bo'lmasligi kerak")
        return value

    def validate_message(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Xabar bo'sh bo'lmasligi kerak")
        return value
