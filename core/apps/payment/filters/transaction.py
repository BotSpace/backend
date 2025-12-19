from django_filters import rest_framework as filters

from core.apps.payment.models import TransactionModel


class TransactionFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = TransactionModel
        fields = [
            "name",
        ]
