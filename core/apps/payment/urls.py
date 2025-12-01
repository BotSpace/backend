from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.payment.views.click import ClickWebhookAPIView
from core.apps.payment.views.payment import payment_link

from .views import HistoryView, TransactionView, PaymeCallBackAPIView

router = DefaultRouter()
router.register("history", HistoryView, basename="history")
router.register("transaction", TransactionView, basename="transaction")
urlpatterns = [
    path("", include(router.urls)),
    path("payment/create-transaction/", payment_link),
    path("payment/click/update/", ClickWebhookAPIView.as_view()),
    path("payment/payme/update/", PaymeCallBackAPIView.as_view()),
]
