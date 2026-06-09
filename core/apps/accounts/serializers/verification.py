from rest_framework import serializers

from core.apps.accounts.models.verification import UserVerificationModel


class VerificationSerializer(serializers.ModelSerializer):
    """Foydalanuvchiga o'z verifikatsiya so'rovini ko'rsatish uchun."""

    class Meta:
        model = UserVerificationModel
        fields = [
            "id",
            "full_name",
            "passport_image",
            "selfie_image",
            "residence_reference",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreateVerificationSerializer(serializers.ModelSerializer):
    """Verifikatsiya hujjatlarini yuborish (multipart)."""

    class Meta:
        model = UserVerificationModel
        fields = [
            "full_name",
            "passport_image",
            "selfie_image",
            "residence_reference",
        ]
