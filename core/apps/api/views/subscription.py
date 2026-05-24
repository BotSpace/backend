# type: ignore
"""
User Subscription API Views
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.apps.api.enums.plan import PlanStatus, PlanType
from core.apps.api.models import PlanModel
from core.apps.api.models.plan import UserSubscription
from core.apps.api.serializers.subscription import (
    SubscriptionSerializer,
    SubscriptionUpgradeSerializer,
    TokenUsageReportSerializer,
)
from core.apps.payment.services.balance import subtract_balance
from core.services.response import error_response, success_response

logger = logging.getLogger(__name__)


def _get_or_create_subscription(user) -> UserSubscription:
    """Foydalanuvchi uchun obuna qaytaradi, bo'lmasa FREE plan bilan yaratadi."""
    try:
        return UserSubscription.objects.select_related("plan").get(user=user)
    except UserSubscription.DoesNotExist:
        free_plan = PlanModel.objects.get(name=PlanType.FREE)
        subscription, _ = UserSubscription.objects.get_or_create(
            user=user,
            defaults={"plan": free_plan, "status": PlanStatus.ACTIVE},
        )
        return subscription


class SubscriptionViewSet(viewsets.ViewSet):
    """
    Foydalanuvchi obunasini boshqarish

    current:      GET  /api/subscription/
    upgrade:      POST /api/subscription/upgrade/
    usage:        GET  /api/subscription/usage/
    report_usage: POST /api/subscription/usage/report/  (ichki endpoint)
    """

    permission_classes = [IsAuthenticated]

    def current(self, request):
        """Joriy foydalanuvchi obunasini qaytaradi."""
        try:
            subscription = _get_or_create_subscription(request.user)
        except PlanModel.DoesNotExist:
            return error_response({"detail": "FREE tarif topilmadi. Admin bilan bog'laning."}, 500)

        serializer = SubscriptionSerializer(subscription)
        return success_response(serializer.data)

    def upgrade(self, request):
        """
        Tarifni yangilash.

        Body: {"plan_id": <int>, "months": <1|3|6|12>}
        """
        try:
            subscription = _get_or_create_subscription(request.user)
        except PlanModel.DoesNotExist:
            return error_response({"detail": "FREE tarif topilmadi. Admin bilan bog'laning."}, 500)

        serializer = SubscriptionUpgradeSerializer(
            data=request.data,
            context={"subscription": subscription},
        )
        if not serializer.is_valid():
            return error_response(serializer.errors, 400)

        new_plan = serializer.validated_data["plan"]
        months = serializer.validated_data.get("months", 1)
        total_price = serializer.validated_data["total_price"]
        old_plan = subscription.plan

        if total_price > 0 and request.user.balance < total_price:
            return error_response({"detail": "Balansda yetarli mablag' mavjud emas."}, 403)

        with transaction.atomic():
            subscription.plan = new_plan
            subscription.status = PlanStatus.ACTIVE
            subscription.expires_at = timezone.now() + timedelta(days=months * 30)
            subscription.save(update_fields=["plan", "status", "expires_at", "updated_at"])

            if total_price > 0:
                subtract_balance(
                    request.user,
                    total_price,
                    f"Tarif yangilandi: {new_plan.get_name_display()} ({months} oy)",
                )

        logger.info(
            "User %s subscription upgraded: %s -> %s (%d oy)",
            request.user.pk,
            old_plan.get_name_display(),
            new_plan.get_name_display(),
            months,
        )

        response_serializer = SubscriptionSerializer(subscription)
        return success_response(
            {
                "message": "Tarif muvaffaqiyatli yangilandi",
                "previous_plan": old_plan.get_name_display(),
                "new_plan": new_plan.get_name_display(),
                "data": response_serializer.data,
            }
        )

    def usage(self, request):
        """Token sarflanishi va bot statistikasini qaytaradi."""
        try:
            subscription = _get_or_create_subscription(request.user)
        except PlanModel.DoesNotExist:
            return error_response({"detail": "FREE tarif topilmadi. Admin bilan bog'laning."}, 500)

        plan = subscription.plan
        output_limit = plan.max_output_tokens
        input_limit = plan.max_input_tokens
        token_limit = input_limit + output_limit
        input_used = subscription.tokens_used_input
        output_used = subscription.tokens_used_output
        token_used = input_used + output_used

        output_used_pct = round(output_used / output_limit * 100, 2) if output_limit else 0
        input_used_pct = round(input_used / input_limit * 100, 2) if input_limit else 0

        return success_response(
            {
                "plan": plan.get_name_display(),
                "status": subscription.status,
                "plan_name": plan.get_name_display(),
                "tokens_used_input": input_used,
                "tokens_used_output": output_used,
                "tokens_limit_input": input_limit,
                "tokens_limit_output": output_limit,
                "tokens_remaining": max(0, token_limit - token_used),
                "bots_count": subscription.bots_count,
                "max_bots": plan.max_bots,
                "usage_percentage": round(token_used / token_limit * 100, 2) if token_limit else 0,
                "ai_token_usage": {
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
                },
                "tokens": {
                    "output": {
                        "used": output_used,
                        "limit": output_limit,
                        "remaining": max(0, output_limit - output_used),
                        "usage_percentage": output_used_pct,
                        "limit_exceeded": output_used >= output_limit if output_limit else False,
                    },
                    "input": {
                        "used": input_used,
                        "limit": input_limit,
                        "remaining": max(0, input_limit - input_used),
                        "usage_percentage": input_used_pct,
                    },
                },
                "bots": {
                    "count": subscription.bots_count,
                    "limit": plan.max_bots,
                    "can_create": subscription.can_create_bot(),
                },
                "token_reset_at": subscription.token_reset_at,
                "expires_at": subscription.expires_at,
            }
        )

    def report_usage(self, request):
        """
        agentv3 dan token sarflanishini qabul qiladi.

        Header:  X-Internal-Token: <settings.INTERNAL_API_TOKEN>
        Body:    {"user_id": <int>, "input_tokens": <int>, "output_tokens": <int>}
        """
        internal_token = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not internal_token:
            return error_response({"detail": "Server konfiguratsiya xatosi."}, 500)

        provided_token = request.headers.get("X-Internal-Token", "")
        if provided_token != internal_token:
            return error_response({"detail": "Ruxsat etilmagan so'rov."}, 403)

        serializer = TokenUsageReportSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, 400)

        user_id = serializer.validated_data["user_id"]
        project_id = serializer.validated_data.get("project_id")
        input_tokens = serializer.validated_data["input_tokens"]
        output_tokens = serializer.validated_data["output_tokens"]

        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response({"detail": "Foydalanuvchi topilmadi."}, 404)

        try:
            subscription = _get_or_create_subscription(user)
        except PlanModel.DoesNotExist:
            return error_response({"detail": "FREE tarif topilmadi. Admin bilan bog'laning."}, 500)

        UserSubscription.objects.filter(pk=subscription.pk).update(
            tokens_used_input=F("tokens_used_input") + input_tokens,
            tokens_used_output=F("tokens_used_output") + output_tokens,
        )

        logger.info(
            "Token usage reported: user=%d project=%d input=%d output=%d",
            user_id,
            project_id,
            input_tokens,
            output_tokens,
        )

        return success_response(
            {
                "user_id": user_id,
                "project_id": project_id,
                "input_tokens_added": input_tokens,
                "output_tokens_added": output_tokens,
            }
        )
