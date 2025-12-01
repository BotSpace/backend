from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.apps.payment.models import TransactionModel
from core.apps.payment.serializers.transaction import (
    CreateTransactionSerializer,
    ListTransactionSerializer,
    RetrieveTransactionSerializer,
)


@extend_schema(tags=["transaction"])
class TransactionView(BaseViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = ListTransactionSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListTransactionSerializer,
        "retrieve": RetrieveTransactionSerializer,
        "create": CreateTransactionSerializer,
    }

    def get_queryset(self):
        return TransactionModel.objects.filter(user=self.request.user)
