from click_up.views import ClickWebhook

from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.services.balance import add_balance, subtract_balance


class ClickWebhookAPIView(ClickWebhook):
    # DRF auth disabled — signature is verified by ClickWebhook.check_auth()
    # using CLICK_SERVICE_ID + CLICK_SECRET_KEY from settings.
    permission_classes = []

    def successfully_payment(self, params):
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

    def cancelled_payment(self, params):
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
