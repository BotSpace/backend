"""Paycue webhook — Humo-karta to'lov tasdig'i.

Paycue WEBHOOK_URL ga POST yuboradi (paycue .env'da sozlanadi → bu endpoint):
  {"action": "confirm" | "cancel", "amount": <int>, "transaction_id": "<uuid>"}
Javob: HTTP 200 {"ok": true}.

transaction_id = order_create paytida saqlangan PaymentOrderModel.external_id.
"""
import logging

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.order import PaymentOrderModel
from core.apps.payment.services.balance import add_balance, subtract_balance
from core.apps.payment.services.commission import calculate_commission
from core.apps.payment.services.notify import notify_bot_payment

logger = logging.getLogger(__name__)


class PaycueWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # Webhook'ni soxtalashtirmaslik uchun X-API-Key tekshiriladi (paycue
        # webhook'ni shu header bilan yuboradi). Webhook kaliti alohida
        # (PAYCUE_WEBHOOK_KEY); bo'sh bo'lsa create kaliti (PAYCUE_API_KEY)
        # ishlatiladi. Kalit umuman yo'q bo'lsa — fail-closed (rad etamiz).
        expected = getattr(settings, "PAYCUE_WEBHOOK_KEY", "") or getattr(settings, "PAYCUE_API_KEY", "")
        provided = request.headers.get("X-API-Key", "")
        if not expected or not constant_time_compare(provided, expected):
            logger.warning("paycue webhook: noto'g'ri yoki yo'q X-API-Key")
            return Response({"ok": False, "detail": "invalid api key"}, status=401)

        action = request.data.get("action")
        transaction_id = request.data.get("transaction_id")
        if not transaction_id:
            return Response({"ok": False, "detail": "transaction_id required"}, status=400)

        order = (
            PaymentOrderModel.objects.filter(external_id=str(transaction_id))
            .select_related("owner", "project")
            .first()
        )
        if order is None:
            # Noma'lum tranzaksiya — ack qaytaramiz (paycue qayta urinmasin).
            logger.warning("paycue webhook: order topilmadi transaction_id=%s", transaction_id)
            return Response({"ok": True})

        if action == "confirm":
            self._confirm(order)
        elif action == "cancel":
            self._cancel(order)
        else:
            logger.warning("paycue webhook: noma'lum action=%s order_id=%s", action, order.pk)

        return Response({"ok": True})

    # ---- confirm/cancel (click oqimiga mos) ----
    def _confirm(self, order: PaymentOrderModel):
        if order.status == PaymentOrderStatusEnum.PAID:
            logger.info("paycue confirm: order #%s allaqachon paid — skip", order.pk)
            return
        if order.status != PaymentOrderStatusEnum.CREATED:
            logger.warning("paycue confirm: order #%s holati %s — skip", order.pk, order.status)
            return

        commission, net_amount = calculate_commission(order.amount)
        add_balance(
            order.owner,
            net_amount,
            f"Bot to'lovi (paycue): {order.comment or order.project.name}",
            idempotency_key=f"payorder:credit:{order.pk}",
        )

        updated = PaymentOrderModel.objects.filter(
            pk=order.pk, status=PaymentOrderStatusEnum.CREATED
        ).update(
            status=PaymentOrderStatusEnum.PAID,
            commission=commission,
            net_amount=net_amount,
            paid_at=timezone.now(),
        )
        if not updated:
            return
        order.refresh_from_db()

        try:
            notify_bot_payment(order)
        except Exception as exc:  # noqa: BLE001 — webhook bloklanmasin
            logger.error("paycue confirm: engine notify xato order_id=%s: %s", order.pk, exc)

    def _cancel(self, order: PaymentOrderModel):
        if order.status == PaymentOrderStatusEnum.CANCELLED:
            return
        if order.status == PaymentOrderStatusEnum.PAID:
            # To'langan bo'lsa — kreditni qaytaramiz.
            subtract_balance(
                order.owner,
                order.net_amount,
                f"Bot to'lovi qaytarildi (paycue): {order.comment or order.project.name}",
                idempotency_key=f"payorder:debit:{order.pk}",
            )
        PaymentOrderModel.objects.filter(pk=order.pk).exclude(
            status=PaymentOrderStatusEnum.CANCELLED
        ).update(status=PaymentOrderStatusEnum.CANCELLED)
        try:
            order.refresh_from_db()
            notify_bot_payment(order, status="failed")
        except Exception as exc:  # noqa: BLE001
            logger.error("paycue cancel: engine notify xato order_id=%s: %s", order.pk, exc)
