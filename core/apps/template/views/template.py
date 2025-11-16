from django_core.mixins import BaseViewSetMixin
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.apps.template.filters.template import TemplateFilter
from core.apps.template.models import TemplateModel, UserTemplateModel
from core.apps.template.serializers.template import (
    CreateTemplateSerializer,
    CreateUsertemplateSerializer,
    ListTemplateSerializer,
    ListUsertemplateSerializer,
    RetrieveTemplateSerializer,
    RetrieveUsertemplateSerializer,
)


@extend_schema(tags=["template"])
class TemplateView(BaseViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = ListTemplateSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TemplateFilter

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


@extend_schema(tags=["usertemplate"])
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
