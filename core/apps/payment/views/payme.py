from payme.views import PaymeWebHookAPIView
from rest_framework.permissions import AllowAny

from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.services.balance import add_balance, subtract_balance


class PaymeCallBackAPIView(PaymeWebHookAPIView):
    # DRF auth disabled — signature is verified by PaymeWebHookAPIView.check_authorize()
    # using PAYME_ID + PAYME_KEY from settings.
    permission_classes = [AllowAny]

    def handle_successfully_payment(self, params, result, *args, **kwargs):
        try:
            transaction = TransactionModel.objects.get(pk=params.merchant_trans_id)
        except TransactionModel.DoesNotExist:
            raise ValueError("Transaction not found")
        add_balance(
            transaction.user,
            transaction.amount,
            "Payme orqali hisob to'ldirildi",
            idempotency_key=f"payme:credit:{params.merchant_trans_id}",
        )
        TransactionModel.objects.filter(pk=transaction.pk, status=False).update(status=True)

    def handle_cancelled_payment(self, params, result, *args, **kwargs):
        try:
            transaction = TransactionModel.objects.get(pk=params.merchant_trans_id)
        except TransactionModel.DoesNotExist:
            raise ValueError("Transaction not found")
        subtract_balance(
            transaction.user,
            transaction.amount,
            "Paymeda to'lov bekor qilindi",
            idempotency_key=f"payme:debit:{params.merchant_trans_id}",
        )
        TransactionModel.objects.filter(pk=transaction.pk, status=True).update(status=False)
