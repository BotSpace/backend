import django_filters

from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.order import PaymentOrderModel


class PaymentOrderFilter(django_filters.FilterSet):
    project_id = django_filters.NumberFilter(field_name="project_id")
    status = django_filters.ChoiceFilter(choices=PaymentOrderStatusEnum.choices)
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    paid_after = django_filters.DateTimeFilter(field_name="paid_at", lookup_expr="gte")
    paid_before = django_filters.DateTimeFilter(field_name="paid_at", lookup_expr="lte")

    class Meta:
        model = PaymentOrderModel
        fields = ["project_id", "status", "created_after", "created_before", "paid_after", "paid_before"]
