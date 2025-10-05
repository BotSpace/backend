from django_filters import rest_framework as filters

from core.apps.api.models import BotModel, ProjectModel


class ProjectFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = ProjectModel
        fields = [
            "name",
        ]


class BotFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = BotModel
        fields = [
            "name",
        ]
