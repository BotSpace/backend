from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.apps.payment.models.withdrawal import WithdrawalRequestModel

MIN_WITHDRAWAL = Decimal("1000")


class WithdrawalSerializer(serializers.ModelSerializer):
    """Foydalanuvchiga o'z pul yechish so'rovlarini ko'rsatish uchun."""

    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = WithdrawalRequestModel
        fields = [
            "id",
            "project",
            "project_name",
            "amount",
            "card_number",
            "card_owner",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "project_name", "status", "rejection_reason", "created_at", "updated_at"]


class CreateWithdrawalSerializer(serializers.ModelSerializer):
    """Pul yechish so'rovini yaratish.

    KYC verifikatsiya, balans yetarliligi va bot egaligi tekshiriladi.
    """

    class Meta:
        model = WithdrawalRequestModel
        fields = ["project", "amount", "card_number", "card_owner"]

    def validate(self, attrs):
        user = self.context["request"].user
        if not getattr(user, "kyc_verified_at", None):
            raise serializers.ValidationError(
                {"detail": _("Pul yechish uchun avval verifikatsiyadan o'tishingiz kerak")}
            )
        return attrs

    def validate_amount(self, value):
        user = self.context["request"].user
        if value < MIN_WITHDRAWAL:
            raise serializers.ValidationError(_("Minimal yechish summasi 1000 so'm"))
        if value > user.balance:
            raise serializers.ValidationError(
                _("Balans yetarli emas. Mavjud: %(balance)s so'm") % {"balance": user.balance}
            )
        return value

    def validate_project(self, value):
        if value is not None and value.owner_id != self.context["request"].user.pk:
            raise serializers.ValidationError(_("Bu bot sizga tegishli emas"))
        return value

    def validate_card_number(self, value):
        card = value.replace(" ", "")
        if not card.isdigit():
            raise serializers.ValidationError(_("Karta raqami faqat raqamlardan iborat bo'lishi kerak"))
        if len(card) < 16 or len(card) > 19:
            raise serializers.ValidationError(_("Karta raqami 16-19 ta raqamdan iborat bo'lishi kerak"))
        return value
