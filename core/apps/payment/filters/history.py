from django_filters import rest_framework as filters

from core.apps.payment.models import HistoryModel


class HistoryFilter(filters.FilterSet):
    class Meta:
        model = HistoryModel
        fields = ["type"]
