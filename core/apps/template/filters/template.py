from django_filters import rest_framework as filters

from core.apps.template.models import TemplateModel


class TemplateFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = TemplateModel
        fields = [
            "name",
        ]
