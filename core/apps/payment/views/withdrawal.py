from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, mixins

from core.apps.payment.enums.withdrawal import WithdrawalStatusEnum
from core.apps.payment.models.withdrawal import WithdrawalRequestModel
from core.apps.payment.serializers.withdrawal import (
    CreateWithdrawalSerializer,
    WithdrawalSerializer,
)


@extend_schema(tags=["payment-withdrawal"])
class WithdrawalView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Bot daromadlaridan pul yechish so'rovlari.

    Foydalanuvchi o'z so'rovlarini ko'radi va yangi so'rov yaratadi.
    Tasdiqlash/rad etish admin panel orqali amalga oshiriladi.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalSerializer

    action_serializer_class = {
        "list": WithdrawalSerializer,
        "retrieve": WithdrawalSerializer,
        "create": CreateWithdrawalSerializer,
    }

    def get_queryset(self):
        return (
            WithdrawalRequestModel.objects.filter(user=self.request.user)
            .select_related("project", "reviewed_by")
            .order_by("-id")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=WithdrawalStatusEnum.PENDING.value)

    def perform_destroy(self, instance):
        if instance.status != WithdrawalStatusEnum.PENDING.value:
            raise ValidationError("Faqat kutilayotgan so'rovni o'chirish mumkin")
        instance.delete()
