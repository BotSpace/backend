from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.apps.template.models import TemplateModel
from core.apps.template.serializers.template import (
    CreateTemplateSerializer,
    ListTemplateSerializer,
    RetrieveTemplateSerializer,
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
