from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.payment.views.click import ClickWebhookAPIView
from core.apps.payment.views.order import EarningsView, order_create, order_status
from core.apps.payment.views.payment import payment_link

from .views import HistoryView, PaymeCallBackAPIView, TransactionView

router = DefaultRouter()
router.register("history", HistoryView, basename="history")
router.register("transaction", TransactionView, basename="transaction")
router.register("earnings", EarningsView, basename="earnings")

urlpatterns = [
    path("", include(router.urls)),
    # Eski endpointlar — o'zgarmaydi
    path("payment/create-transaction/", payment_link),
    path("payment/click/update/", ClickWebhookAPIView.as_view()),
    path("payment/payme/update/", PaymeCallBackAPIView.as_view()),
    # Yangi platforma to'lov endpointlari
    path("payment/order/create/", order_create, name="payment-order-create"),
    path("payment/order/<int:order_id>/status/", order_status, name="payment-order-status"),
]
