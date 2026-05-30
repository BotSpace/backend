# type: ignore
from rest_framework import serializers

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    reviewed_by_phone = serializers.CharField(source="reviewed_by.phone", read_only=True)

    class Meta:
        model = TemplateWithdrawalRequestModel
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
            "user_phone",
            "amount",
            "card_number",
            "card_owner",
            "status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_by_phone",
            "created_at",
            "updated_at",
        )


class AdminWithdrawalApproveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminWithdrawalRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500)
