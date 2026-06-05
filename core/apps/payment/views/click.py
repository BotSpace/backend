import logging

from django.utils import timezone
from click_up.views import ClickWebhook

from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.services.balance import add_balance, subtract_balance
from core.apps.payment.services.commission import calculate_commission

logger = logging.getLogger(__name__)

_ORDER_PREFIX = "ord_"


def _is_order(merchant_trans_id) -> bool:
    return str(merchant_trans_id).startswith(_ORDER_PREFIX)


def _order_pk(merchant_trans_id) -> int:
    return int(str(merchant_trans_id)[len(_ORDER_PREFIX):])


class ClickWebhookAPIView(ClickWebhook):
    # DRF auth disabled — signature is verified by ClickWebhook.check_auth()
    # using CLICK_SERVICE_ID + CLICK_SECRET_KEY from settings.
    permission_classes = []

    def successfully_payment(self, params):
        if _is_order(params.merchant_trans_id):
            self._order_success(params)
        else:
            self._transaction_success(params)

    def cancelled_payment(self, params):
        if _is_order(params.merchant_trans_id):
            self._order_cancelled(params)
        else:
            self._transaction_cancelled(params)

    # ---------- PaymentOrder oqimi ----------

    def _order_success(self, params):
        from core.apps.payment.models.order import PaymentOrderModel
        from core.apps.payment.services.notify import notify_bot_payment

        pk = _order_pk(params.merchant_trans_id)
        try:
            order = PaymentOrderModel.objects.get(pk=pk)
        except PaymentOrderModel.DoesNotExist:
            raise ValueError(f"PaymentOrder #{pk} topilmadi")

        # Idempotency: allaqachon to'langan bo'lsa o'tkazib yuboramiz
        if order.status == PaymentOrderStatusEnum.PAID:
            logger.info("_order_success: order #%s allaqachon paid — skip", pk)
            return

        if order.status != PaymentOrderStatusEnum.CREATED:
            logger.warning("_order_success: order #%s holati %s — skip", pk, order.status)
            return

        commission, net_amount = calculate_commission(order.amount)

        # Egaga net kredit
        add_balance(
            order.owner,
            net_amount,
            f"Bot to'lovi: {order.comment or order.project.name}",
            idempotency_key=f"payorder:credit:{order.pk}",
        )

        # Botspace komissiya
        self._credit_botspace(order, commission)

        # Order holati yangilash
        external_id = getattr(params, "click_trans_id", None) or getattr(params, "transaction_id", None)
        PaymentOrderModel.objects.filter(pk=order.pk, status=PaymentOrderStatusEnum.CREATED).update(
            status=PaymentOrderStatusEnum.PAID,
            commission=commission,
            net_amount=net_amount,
            paid_at=timezone.now(),
            external_id=str(external_id) if external_id else None,
        )
        order.refresh_from_db()

        # Engine'ni xabardor qilish — xato bo'lsa webhook bloklanmaydi
        try:
            notify_bot_payment(order)
        except Exception as exc:
            logger.error("_order_success: engine notify xato order_id=%s: %s", pk, exc)

    def _order_cancelled(self, params):
        from core.apps.payment.models.order import PaymentOrderModel

        pk = _order_pk(params.merchant_trans_id)
        try:
            order = PaymentOrderModel.objects.get(pk=pk)
        except PaymentOrderModel.DoesNotExist:
            raise ValueError(f"PaymentOrder #{pk} topilmadi")

        if order.status == PaymentOrderStatusEnum.CANCELLED:
            logger.info("_order_cancelled: order #%s allaqachon cancelled — skip", pk)
            return

        # Agar to'lov kreditlangan bo'lsa — qaytaramiz (refund)
        if order.status == PaymentOrderStatusEnum.PAID:
            net_amount = order.net_amount
            subtract_balance(
                order.owner,
                net_amount,
                f"Bot to'lovi qaytarildi: {order.comment or order.project.name}",
                idempotency_key=f"payorder:debit:{order.pk}",
            )

        PaymentOrderModel.objects.filter(pk=order.pk).exclude(
            status=PaymentOrderStatusEnum.CANCELLED
        ).update(status=PaymentOrderStatusEnum.CANCELLED)

    def _credit_botspace(self, order, commission):
        """Botspace daromad hisobiga komissiya yozadi.

        TODO Faza4: settings'dan BOTSPACE_REVENUE_USER_ID o'qib to'g'ri userga kredit qilish.
        Hozir komissiya logga yoziladi, egaga net to'g'ri kreditlanadi.
        """
        from django.conf import settings
        from django.contrib.auth import get_user_model

        revenue_user_id = getattr(settings, "BOTSPACE_REVENUE_USER_ID", None)
        if not revenue_user_id:
            logger.info(
                "_credit_botspace: BOTSPACE_REVENUE_USER_ID sozlanmagan, "
                "komissiya=%s order_id=%s (TODO Faza4)",
                commission,
                order.pk,
            )
            return

        User = get_user_model()
        try:
            revenue_user = User.objects.get(pk=revenue_user_id)
            add_balance(
                revenue_user,
                commission,
                f"Botspace komissiya: order #{order.pk}",
                idempotency_key=f"payorder:fee:{order.pk}",
            )
        except User.DoesNotExist:
            logger.warning(
                "_credit_botspace: BOTSPACE_REVENUE_USER_ID=%s topilmadi, "
                "komissiya=%s yo'qotilmadi — order_id=%s (TODO Faza4)",
                revenue_user_id,
                commission,
                order.pk,
            )

    # ---------- Eski TransactionModel oqimi (O'ZGARTIRMA) ----------

    def _transaction_success(self, params):
        try:
            transaction = TransactionModel.objects.get(pk=params.merchant_trans_id)
        except TransactionModel.DoesNotExist:
            raise ValueError("Transaction not found")
        add_balance(
            transaction.user,
            transaction.amount,
            "Click orqali hisob to'ldirildi",
            idempotency_key=f"click:credit:{params.merchant_trans_id}",
        )
        TransactionModel.objects.filter(pk=transaction.pk, status=False).update(status=True)

    def _transaction_cancelled(self, params):
        try:
            transaction = TransactionModel.objects.get(pk=params.merchant_trans_id)
        except TransactionModel.DoesNotExist:
            raise ValueError("Transaction not found")
        subtract_balance(
            transaction.user,
            transaction.amount,
            "Clickdan to'lov bekor qilindi",
            idempotency_key=f"click:debit:{params.merchant_trans_id}",
        )
        TransactionModel.objects.filter(pk=transaction.pk, status=True).update(status=False)
