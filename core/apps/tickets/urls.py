from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.tickets.views.ticket import TicketView

router = DefaultRouter()
router.register("ticket", TicketView, basename="ticket")

urlpatterns = [
    path("", include(router.urls)),
]
