from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    ai_token_usage = serializers.SerializerMethodField()
    is_kyc_verified = serializers.SerializerMethodField()

    class Meta:
        exclude = [
            "created_at",
            "updated_at",
            "password",
            "groups",
            "user_permissions"
        ]
        model = get_user_model()

    def get_is_kyc_verified(self, obj) -> bool:
        return obj.kyc_verified_at is not None

    def get_ai_token_usage(self, obj):
        from core.apps.api.enums.plan import PlanStatus, PlanType
        from core.apps.api.models import PlanModel
        from core.apps.api.models.plan import UserSubscription

        try:
            subscription = UserSubscription.objects.select_related("plan").get(user=obj)
        except UserSubscription.DoesNotExist:
            free_plan = PlanModel.objects.filter(name=PlanType.FREE).first()
            if free_plan is None:
                return None
            subscription, _ = UserSubscription.objects.get_or_create(
                user=obj,
                defaults={"plan": free_plan, "status": PlanStatus.ACTIVE},
            )

        plan = subscription.plan
        input_used = subscription.tokens_used_input
        output_used = subscription.tokens_used_output
        token_limit = plan.max_input_tokens + plan.max_output_tokens
        token_used = input_used + output_used

        return {
            "limit": token_limit,
            "used": token_used,
            "remaining": max(0, token_limit - token_used),
            "input_used": input_used,
            "output_used": output_used,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "display": plan.get_name_display(),
            },
            "status": subscription.status,
            "token_reset_at": subscription.token_reset_at,
        }


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "first_name",
            "last_name"
        ]
