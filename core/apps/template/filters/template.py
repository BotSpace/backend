from django.db.models import Q
from django_filters import rest_framework as filters

from core.apps.template.models import TemplateModel


class TemplateFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    price = filters.RangeFilter(field_name="original_price")

    class Meta:
        model = TemplateModel
        fields = [
            "categories",
            "features",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(description=value) | Q(short_description=value | Q(name=value)),
        )
