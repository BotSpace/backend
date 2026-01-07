from django_core.mixins import BaseViewSetMixin
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.apps.template.filters.template import TemplateFilter
from core.apps.template.models import TemplateModel, UserTemplateModel
from core.apps.template.models.template import TemplateCategoryModel, TemplateFeatureModel
from core.apps.template.serializers.template import (
    CreateTemplateSerializer,
    CreateUsertemplateSerializer,
    ListTemplateSerializer,
    ListUsertemplateSerializer,
    RetrieveTemplateSerializer,
    RetrieveUsertemplateSerializer,
)
from core.apps.template.serializers.template.category import (
    CreateTemplateCategorySerializer,
    ListTemplateCategorySerializer,
    RetrieveTemplateCategorySerializer,
)
from core.apps.template.serializers.template.feature import (
    CreateTemplateFeatureSerializer,
    ListTemplateFeatureSerializer,
    RetrieveTemplateFeatureSerializer,
)


@extend_schema(tags=["template"])
class TemplateView(BaseViewSetMixin, ReadOnlyModelViewSet):
    queryset = TemplateModel.objects.filter(is_verify=True)
    serializer_class = ListTemplateSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TemplateFilter
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTemplateSerializer,
        "retrieve": RetrieveTemplateSerializer,
        "create": CreateTemplateSerializer,
    }

    def get_queryset(self):
        return TemplateModel.objects.filter(is_verify=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save()
        serializer = self.get_serializer(instance=instance)
        return Response(data=serializer.data)


@extend_schema(tags=["template"])
class TemplateCategoryView(BaseViewSetMixin, ReadOnlyModelViewSet):
    queryset = TemplateCategoryModel.objects.all()
    serializer_class = ListTemplateCategorySerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTemplateCategorySerializer,
        "retrieve": RetrieveTemplateCategorySerializer,
        "create": CreateTemplateCategorySerializer,
    }

    def get_queryset(self):
        return TemplateCategoryModel.objects.all()


@extend_schema(tags=["template"])
class TemplateFeatureView(BaseViewSetMixin, ReadOnlyModelViewSet):
    queryset = TemplateFeatureModel.objects.all()
    serializer_class = ListTemplateFeatureSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTemplateFeatureSerializer,
        "retrieve": RetrieveTemplateFeatureSerializer,
        "create": CreateTemplateFeatureSerializer,
    }

    def get_queryset(self):
        return TemplateFeatureModel.objects.all()


@extend_schema(tags=["template"])
class UsertemplateView(BaseViewSetMixin, ReadOnlyModelViewSet):
    queryset = UserTemplateModel.objects.all()
    serializer_class = ListUsertemplateSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListUsertemplateSerializer,
        "retrieve": RetrieveUsertemplateSerializer,
        "create": CreateUsertemplateSerializer,
    }
