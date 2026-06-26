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
from rest_framework.permissions import AllowAny, IsAuthenticated

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

    def get_permissions(self):
        # report_usage agentv3 dan X-Internal-Token bilan chaqiriladi.
        # DRF default Bearer JWT autentifikatsiyasi bu yerda 401 qaytarmasligi
        # uchun shu action uchun ochiq qilamiz — view ichidagi mantiq
        # X-Internal-Token ni alohida tekshiradi.
        if getattr(self, "action", None) == "report_usage":
            return [AllowAny()]
        return [permission() for permission in self.permission_classes]

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
        token_limit = plan.max_tokens
        input_used = subscription.tokens_used_input
        output_used = subscription.tokens_used_output
        token_used = input_used + output_used
        tokens_remaining = max(0, token_limit - token_used)
        usage_pct = round(token_used / token_limit * 100, 2) if token_limit else 0

        return success_response(
            {
                "plan": plan.get_name_display(),
                "status": subscription.status,
                "plan_name": plan.get_name_display(),
                "tokens_used_input": input_used,
                "tokens_used_output": output_used,
                "tokens_limit": token_limit,
                "tokens_remaining": tokens_remaining,
                "bots_count": subscription.bots_count,
                "max_bots": plan.max_bots,
                "usage_percentage": usage_pct,
                "ai_token_usage": {
                    "limit": token_limit,
                    "used": token_used,
                    "remaining": tokens_remaining,
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
                    "total": {
                        "used": token_used,
                        "limit": token_limit,
                        "remaining": tokens_remaining,
                        "usage_percentage": usage_pct,
                        "limit_exceeded": token_used >= token_limit if token_limit else False,
                    },
                    "input_used": input_used,
                    "output_used": output_used,
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
        cache_read_tokens = serializer.validated_data.get("cache_read_tokens", 0)

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

        # Keshlangan tokenlar arzonroq — planга bog'liq koeffitsient bilan hisoblanadi.
        # cache_read ni input_tokens dan oshib ketmasligiga ishonch hosil qilamiz.
        cache_read = max(0, min(cache_read_tokens, input_tokens))
        uncached = input_tokens - cache_read
        billable_input = uncached + round(cache_read * subscription.plan.cached_token_rate)

        UserSubscription.objects.filter(pk=subscription.pk).update(
            tokens_used_input=F("tokens_used_input") + billable_input,
            tokens_used_output=F("tokens_used_output") + output_tokens,
        )

        # AI'dan foydalanish metrikalari (vaqt bo'yicha grafik uchun).
        from core.apps.shared.observability import metrics

        metrics.safe_inc(metrics.AI_RUNS)
        metrics.safe_inc(metrics.AI_TOKENS, billable_input, kind="input")
        metrics.safe_inc(metrics.AI_TOKENS, output_tokens, kind="output")

        logger.info(
            "Token usage reported: user=%d project=%s input=%d cache_read=%d billable_input=%d output=%d",
            user_id,
            project_id,
            input_tokens,
            cache_read,
            billable_input,
            output_tokens,
        )

        return success_response(
            {
                "user_id": user_id,
                "project_id": project_id,
                "input_tokens_added": billable_input,
                "output_tokens_added": output_tokens,
            }
        )
