# type: ignore
from decimal import Decimal
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework import status

from core.apps.template.enums.order import TemplateOrderStatusEnum
from core.apps.template.models import TemplateOrderModel
from core.apps.template.serializers.order import (
    CreateTemplateOrderSerializer,
    ListTemplateOrderSerializer,
    RetrieveTemplateOrderSerializer,
)


@extend_schema(tags=["order"])
class TemplateOrderView(BaseViewSetMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    serializer_class = ListTemplateOrderSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTemplateOrderSerializer,
        "retrieve": RetrieveTemplateOrderSerializer,
        "create": CreateTemplateOrderSerializer,
    }

    def get_queryset(self):
        return TemplateOrderModel.objects.filter(user=self.request.user).order_by("-id")

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        instance = TemplateOrderModel.objects.filter(template_id=data.get("template"), user=request.user).first()
        if instance is not None:
            return Response(self.get_serializer(instance=instance).data, status=status.HTTP_200_OK)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        data = serializer.validated_data
        amount = data["template"].price
        status = TemplateOrderStatusEnum.PENDING.value
        payment_status = False
        if amount == Decimal("0.00"):
            status = TemplateOrderStatusEnum.CONFIRM.value
            payment_status = True
        return serializer.save(user=self.request.user, amount=amount, status=status, payment_status=payment_status)
