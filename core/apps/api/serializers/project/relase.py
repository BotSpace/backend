from rest_framework import serializers

from core.apps.api.models import RelaseModel

# Billing period discounts (matches frontend BILLING_PERIODS)
BILLING_MONTHS_DISCOUNTS = {1: 0, 3: 12, 6: 20, 12: 30}


def calculate_total_price(monthly_price, months):
    """Calculate total price with discount for a given billing period."""
    discount = BILLING_MONTHS_DISCOUNTS.get(months, 0)
    discounted_monthly = round(float(monthly_price) * (1 - discount / 100))
    return discounted_monthly * months


class BaseRelaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelaseModel
        fields = [
            "id",
            "version",
            "status",
            "service_id",
        ]


class ListRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta): ...


class RetrieveRelaseSerializer(BaseRelaseSerializer):
    class Meta(BaseRelaseSerializer.Meta):
        fields = [
            "id",
            "project",
            "version",
            "status",
            "service_id",
            "flow",
        ]


class CreateRelaseSerializer(BaseRelaseSerializer):
    plan_id = serializers.IntegerField(
        required=False,
        write_only=True,
        help_text="Legacy maydon. Loyiha tariflari endi ishlatilmaydi.",
    )
    months = serializers.IntegerField(
        required=False,
        write_only=True,
        default=1,
        help_text="Legacy maydon. Loyiha tariflari endi ishlatilmaydi.",
    )

    def validate_months(self, value):
        if value not in BILLING_MONTHS_DISCOUNTS:
            raise serializers.ValidationError(
                "Noto'g'ri muddat. Quyidagilardan birini tanlang: 1, 3, 6, 12.",
                code="invalid_billing_months",
            )
        return value

    def validate(self, attrs):
        attrs.pop("plan_id", None)
        attrs.pop("months", None)
        return attrs

    class Meta(BaseRelaseSerializer.Meta):
        fields = [
            "id",
            "project",
            "version",
            "plan_id",
            "months",
        ]
        extra_kwargs = {"version": {"read_only": True}}
