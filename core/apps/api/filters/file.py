from django_filters import rest_framework as filters

from core.apps.api.models import FileModel


class FileFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = FileModel
        fields = [
            "name",
        ]
