from rest_framework import serializers

from core.apps.api.enums.plan import PlanType
from core.apps.api.models import PlanModel, RelaseModel

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
        help_text=(
            "Tarif ID. Faqat birinchi release uchun majburiy. "
            "Loyihada allaqachon release bo'lsa, bu maydon e'tiborga olinmaydi."
        ),
    )
    months = serializers.IntegerField(
        required=False,
        write_only=True,
        default=1,
        help_text="To'lov muddati (oy): 1, 3, 6, yoki 12.",
    )

    def validate_months(self, value):
        if value not in BILLING_MONTHS_DISCOUNTS:
            raise serializers.ValidationError(
                "Noto'g'ri muddat. Quyidagilardan birini tanlang: 1, 3, 6, 12.",
                code="invalid_billing_months",
            )
        return value

    def validate(self, attrs):
        project = attrs.get("project")
        plan_id = attrs.get("plan_id")
        months = attrs.pop("months", 1)

        # Loyihada allaqachon release bor bo'lsa, plan so'ralmaydi
        has_release = RelaseModel.objects.filter(project=project).exists()
        if has_release:
            attrs.pop("plan_id", None)
            return attrs

        # Birinchi release: plan_id majburiy
        if not plan_id:
            raise serializers.ValidationError(
                {"plan_id": "Birinchi release uchun tarif tanlash majburiy"},
                code="plan_required",
            )

        try:
            plan = PlanModel.objects.get(id=plan_id, is_active=True)
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError(
                {"plan_id": "Noto'g'ri yoki nofaol tarif"},
                code="plan_inactive",
            )

        user = self.context["request"].user

        # Foydalanuvchining biror loyihasida FREE plan bilan release qilinganligini tekshirish
        user_has_free_release = RelaseModel.objects.filter(
            project__owner=user,
            project__plan_subscription__plan__name=PlanType.FREE.value,
        ).exists()

        if user_has_free_release and plan.name == PlanType.FREE.value:
            raise serializers.ValidationError(
                {"plan_id": "Siz allaqachon bepul tarifdan foydalangansiz. Pulli tarif tanlash majburiy"},
                code="paid_plan_required",
            )

        total_price = calculate_total_price(plan.price, months)

        if total_price > 0:
            if user.balance < total_price:
                raise serializers.ValidationError(
                    {
                        "plan_id": "Balansingiz yetarli emas. Kerakli: {}, Mavjud: {}".format(
                            total_price, user.balance
                        )
                    },
                    code="insufficient_balance",
                )

        attrs["_plan"] = plan
        attrs["_months"] = months
        attrs["_total_price"] = total_price
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
