from django_filters import rest_framework as filters

from core.apps.template.models import TemplateModel, UserTemplateModel


class TemplateFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    price = filters.RangeFilter(field_name="original_price")

    class Meta:
        model = TemplateModel
        fields = [
            "categories",
            "features",
            "short_description",
            "description",
        ]
