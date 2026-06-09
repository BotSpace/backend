from rest_framework import serializers

from core.apps.tickets.models.ticket import TicketMessageModel, TicketModel


class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessageModel
        fields = ["id", "sender", "message", "attachment", "created_at"]
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    """Murojaat + uning suhbati (xabarlar)."""

    messages = TicketMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = TicketModel
        fields = ["id", "subject", "status", "created_at", "updated_at", "last_message", "messages"]
        read_only_fields = fields

    def get_last_message(self, obj):
        last = obj.messages.all().last() if hasattr(obj, "messages") else None
        if last is None:
            return None
        return {"sender": last.sender, "message": last.message}


class CreateTicketSerializer(serializers.Serializer):
    """Yangi murojaat: sarlavha + birinchi xabar (+ ixtiyoriy fayl)."""

    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    attachment = serializers.FileField(required=False, allow_null=True)

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


class CreateMessageSerializer(serializers.Serializer):
    """Mavjud murojaatga xabar qo'shish."""

    message = serializers.CharField()
    attachment = serializers.FileField(required=False, allow_null=True)

    def validate_message(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Xabar bo'sh bo'lmasligi kerak")
        return value
