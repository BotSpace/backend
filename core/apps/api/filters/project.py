from django_filters import rest_framework as filters

from core.apps.api.models import BotModel, FlowModel, ProjectModel, RelaseModel


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


class FlowFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = FlowModel
        fields = [
            "name",
        ]


class RelaseFilter(filters.FilterSet):
    # name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = RelaseModel
        fields = [
            "name",
        ]
