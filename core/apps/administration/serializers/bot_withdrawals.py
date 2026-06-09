# type: ignore
from rest_framework import serializers

from core.apps.payment.models.withdrawal import WithdrawalRequestModel


class AdminBotWithdrawalSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    reviewed_by_phone = serializers.CharField(source="reviewed_by.phone", read_only=True)

    class Meta:
        model = WithdrawalRequestModel
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
            "user_phone",
            "project",
            "project_name",
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


class AdminBotWithdrawalApproveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminBotWithdrawalRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500)
