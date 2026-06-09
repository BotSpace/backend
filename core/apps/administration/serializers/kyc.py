# type: ignore
from rest_framework import serializers

from core.apps.accounts.models.verification import UserVerificationModel


class AdminKycSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    reviewed_by_phone = serializers.CharField(source="reviewed_by.phone", read_only=True)

    class Meta:
        model = UserVerificationModel
        fields = (
            "id",
            "user",
            "user_phone",
            "full_name",
            "passport_image",
            "selfie_image",
            "residence_reference",
            "status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_by_phone",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminKycApproveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminKycRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500)
