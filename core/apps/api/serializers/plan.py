# type: ignore
"""
Plan serializers
"""
from rest_framework import serializers
from core.apps.api.models import PlanModel, ProjectPlanModel
from core.apps.api.serializers.project.relase import BILLING_MONTHS_DISCOUNTS, calculate_total_price


class PlanSerializer(serializers.ModelSerializer):
    """Tarif serializer"""

    name_display = serializers.CharField(source="get_name_display", read_only=True)

    class Meta:
        model = PlanModel
        fields = [
            "id",
            "name",
            "name_display",
            "price",
            "max_users",
            "max_bots",
            "max_output_tokens",
            "max_input_tokens",
            "features",
            "powered_by_botmother",
            "custom_domain",
            "is_top",
            "priority_support",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "name_display"]


class ProjectPlanSerializer(serializers.ModelSerializer):
    """Proyekt tarifi serializer"""

    plan_details = PlanSerializer(source="plan", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    limit_exceeded = serializers.BooleanField(source="is_limit_exceeded", read_only=True)
    can_add_user = serializers.BooleanField(read_only=True)

    # Grace period info
    days_until_suspension = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPlanModel
        fields = [
            "id",
            "project",
            "plan",
            "plan_details",
            "status",
            "status_display",
            "current_users",
            "limit_exceeded",
            "can_add_user",
            "limit_exceeded_at",
            "grace_period_notified",
            "days_until_suspension",
            "started_at",
            "expires_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "current_users",
            "limit_exceeded_at",
            "grace_period_notified",
            "started_at",
            "created_at",
        ]

    def get_days_until_suspension(self, obj):
        """Calculate days remaining until suspension"""
        if not obj.limit_exceeded_at:
            return None

        from django.utils import timezone
        from datetime import timedelta

        grace_period_end = obj.limit_exceeded_at + timedelta(days=3)
        now = timezone.now()

        if now >= grace_period_end:
            return 0

        days_left = (grace_period_end - now).days
        return max(0, days_left)


class ProjectPlanUpgradeSerializer(serializers.Serializer):
    """Tarif yangilash serializer"""

    plan_id = serializers.IntegerField(required=True)
    months = serializers.IntegerField(required=False, default=1)

    def validate_plan_id(self, value):
        """Validate plan exists and is active"""
        try:
            plan = PlanModel.objects.get(id=value, is_active=True)
            return plan
        except PlanModel.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan")

    def validate_months(self, value):
        if value not in BILLING_MONTHS_DISCOUNTS:
            raise serializers.ValidationError(
                "Noto'g'ri muddat. Quyidagilardan birini tanlang: 1, 3, 6, 12."
            )
        return value

    def validate(self, attrs):
        """Validate upgrade is allowed"""
        plan = attrs["plan_id"]
        months = attrs.get("months", 1)
        project_plan = self.context.get("project_plan")

        if not project_plan:
            raise serializers.ValidationError("Project plan not found")

        current_plan = project_plan.plan

        if plan.id == current_plan.id:
            raise serializers.ValidationError("Already on this plan")

        # Can't downgrade during grace period or suspension
        if project_plan.status in ["grace_period", "suspended"]:
            if plan.max_users < current_plan.max_users:
                raise serializers.ValidationError(
                    "Cannot downgrade while in grace period or suspended. "
                    "Please upgrade to handle current user load first."
                )

        attrs["plan"] = plan
        attrs["total_price"] = calculate_total_price(plan.price, months)
        return attrs
