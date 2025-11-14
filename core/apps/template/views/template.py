from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

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
    queryset = TemplateModel.objects.all()
    serializer_class = ListTemplateSerializer
    permission_classes = [AllowAny]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTemplateSerializer,
        "retrieve": RetrieveTemplateSerializer,
        "create": CreateTemplateSerializer,
    }


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
