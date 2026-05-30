# type: ignore
"""Read-only payment transaction history for admins."""

from django.db.models import Q
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework import serializers as drf_serializers

from core.apps.administration.permissions import IsAdminUser
from core.apps.payment.models.transaction import TransactionModel


class _TransactionSerializer(drf_serializers.ModelSerializer):
    user_phone = drf_serializers.CharField(source="user.phone", read_only=True)
    user_id = drf_serializers.IntegerField(read_only=True)

    class Meta:
        model = TransactionModel
        fields = "__all__"
        # View is list/retrieve only — no write path, so explicit
        # read_only_fields aren't needed.


class AdminTransactionsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = _TransactionSerializer

    def get_queryset(self):
        qs = TransactionModel.objects.select_related("user").order_by("-id")
        p = self.request.query_params
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(user__phone__icontains=search)
                | Q(idempotency_key__icontains=search)
            )
        user = p.get("user", "").strip()
        if user.isdigit():
            qs = qs.filter(user_id=int(user))
        # status is a BooleanField (paid/unpaid)
        status = p.get("status", "").strip()
        if status in ("true", "false"):
            qs = qs.filter(status=(status == "true"))
        amount_min = p.get("amount_min", "").strip()
        if amount_min.replace(".", "", 1).isdigit():
            qs = qs.filter(amount__gte=amount_min)
        amount_max = p.get("amount_max", "").strip()
        if amount_max.replace(".", "", 1).isdigit():
            qs = qs.filter(amount__lte=amount_max)
        created_after = p.get("created_after", "").strip()
        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
        created_before = p.get("created_before", "").strip()
        if created_before:
            qs = qs.filter(created_at__date__lte=created_before)
        ordering = p.get("ordering", "").strip()
        if ordering in ("id", "-id", "amount", "-amount", "created_at", "-created_at"):
            qs = qs.order_by(ordering)
        return qs
