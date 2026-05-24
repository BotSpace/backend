# type: ignore
"""
Plan API Views
"""
from rest_framework import viewsets

from core.apps.api.models import PlanModel
from core.apps.api.serializers.plan import PlanSerializer
from django_core.mixins import BaseViewSetMixin


class PlanViewSet(BaseViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Tariflarni ko'rish API

    list: Barcha aktiv tariflarni olish
    retrieve: Bitta tarifni ko'rish
    """

    queryset = PlanModel.objects.filter(is_active=True).order_by("-id")
    serializer_class = PlanSerializer
    permission_classes = []

    def get_queryset(self):
        """Filter only active plans, ordered by price."""
        return PlanModel.objects.filter(is_active=True).order_by("order")
