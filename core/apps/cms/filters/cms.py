from django_filters import rest_framework as filters

from core.apps.cms.models import CollectionModel


class CollectionFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = CollectionModel
        fields = [
            "name",
        ]
