# type: ignore
"""Read-only payment transaction history for admins."""

from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework import serializers as drf_serializers

from core.apps.administration.permissions import IsAdminUser
from core.apps.payment.models.transaction import TransactionModel


class _TransactionSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = TransactionModel
        fields = "__all__"
        # View is list/retrieve only — no write path, so explicit
        # read_only_fields aren't needed.


class AdminTransactionsView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = _TransactionSerializer

    def get_queryset(self):
        qs = TransactionModel.objects.all().order_by("-id")
        provider = self.request.query_params.get("provider", "").strip()
        if provider:
            qs = qs.filter(provider__iexact=provider) if hasattr(TransactionModel, "provider") else qs
        return qs
