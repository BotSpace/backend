from django_filters import rest_framework as filters

from core.apps.payment.models import TransactionModel


class TransactionFilter(filters.FilterSet):
    class Meta:
        model = TransactionModel
        fields = ["status"]
