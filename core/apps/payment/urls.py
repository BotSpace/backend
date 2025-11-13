from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TransactionView

router = DefaultRouter()
router.register("transaction", TransactionView, basename="transaction")
urlpatterns = [path("", include(router.urls))]
