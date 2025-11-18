from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.payment.views.payment import payment_link

from .views import TransactionView

router = DefaultRouter()
router.register("transaction", TransactionView, basename="transaction")
urlpatterns = [
    path("", include(router.urls)),
    path("payment/create-transaction/", payment_link),
]
