# type: ignore
"""
Subscription serializers
"""
from rest_framework import serializers

from core.apps.api.models import PlanModel
from core.apps.api.models.plan import UserSubscription
from core.apps.api.serializers.plan import PlanSerializer
from core.apps.api.serializers.project.relase import BILLING_MONTHS_DISCOUNTS, calculate_total_price


class SubscriptionSerializer(serializers.ModelSerializer):
    """Foydalanuvchi obunasi serializer"""

    plan_details = PlanSerializer(source="plan", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tokens_remaining = serializers.IntegerField(read_only=True)
    is_token_limit_exceeded = serializers.BooleanField(read_only=True)
    can_create_bot = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "plan_details",
            "status",
            "status_display",
            "started_at",
            "expires_at",
            "tokens_used_input",
            "tokens_used_output",
            "tokens_remaining",
            "is_token_limit_exceeded",
            "bots_count",
            "can_create_bot",
            "token_reset_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "started_at",
            "tokens_used_input",
            "tokens_used_output",
            "bots_count",
            "token_reset_at",
            "created_at",
        ]


class SubscriptionUpgradeSerializer(serializers.Serializer):
    """Tarif yangilash serializer"""

    plan_id = serializers.IntegerField(required=True)
    months = serializers.IntegerField(required=False, default=1)

    def validate_plan_id(self, value):
        try:
            plan = PlanModel.objects.get(id=value, is_active=True)
            return plan
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError("Tarif topilmadi yoki nofaol")

    def validate_months(self, value):
        if value not in BILLING_MONTHS_DISCOUNTS:
            raise serializers.ValidationError(
                "Noto'g'ri muddat. Quyidagilardan birini tanlang: 1, 3, 6, 12."
            )
        return value

    def validate(self, attrs):
        plan = attrs["plan_id"]
        months = attrs.get("months", 1)
        subscription = self.context.get("subscription")

        if not subscription:
            raise serializers.ValidationError("Obuna topilmadi")

        if plan.id == subscription.plan_id:
            raise serializers.ValidationError("Siz allaqachon ushbu tarifdasiz")

        attrs["plan"] = plan
        attrs["total_price"] = calculate_total_price(plan.price, months)
        return attrs


class TokenUsageReportSerializer(serializers.Serializer):
    """Token sarflanishi hisoboti serializer (agentv3 ichki endpointi uchun)"""

    user_id = serializers.IntegerField(required=True)
    project_id = serializers.IntegerField(required=True)
    input_tokens = serializers.IntegerField(required=True, min_value=0)
    output_tokens = serializers.IntegerField(required=True, min_value=0)

    def validate_user_id(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Foydalanuvchi topilmadi")
        return value

    def validate_project_id(self, value):
        from core.apps.api.models import ProjectModel

        if not ProjectModel.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Loyiha topilmadi")
        return value
