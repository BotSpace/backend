# type: ignore
"""Read-only bot payment orders (botdan tushgan to'lovlar) for admins.

Filterable by `project` (bot) and `owner` (user) so the admin panel can show:
  - bot detail   → that bot's incoming payments      (?project=<id>)
  - user detail  → payments across the user's bots    (?owner=<id>)
"""

from django.db.models import Q
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework import serializers as drf_serializers

from core.apps.administration.permissions import IsAdminUser
from core.apps.payment.models.order import PaymentOrderModel


class _OrderSerializer(drf_serializers.ModelSerializer):
    project_name = drf_serializers.CharField(source="project.name", read_only=True)
    owner_phone = drf_serializers.CharField(source="owner.phone", read_only=True)
    payer_name = drf_serializers.SerializerMethodField()

    class Meta:
        model = PaymentOrderModel
        fields = [
            "id",
            "project",
            "project_name",
            "owner",
            "owner_phone",
            "payer_chat_id",
            "payer_first_name",
            "payer_last_name",
            "payer_username",
            "payer_name",
            "amount",
            "commission",
            "net_amount",
            "provider",
            "status",
            "comment",
            "paid_at",
            "is_debug",
            "created_at",
            "updated_at",
        ]

    def get_payer_name(self, obj):
        full = " ".join(p for p in [obj.payer_first_name or "", obj.payer_last_name or ""] if p).strip()
        if full:
            return full
        return f"@{obj.payer_username}" if obj.payer_username else None


class AdminBotOrdersView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = _OrderSerializer

    def get_queryset(self):
        qs = PaymentOrderModel.objects.select_related("project", "owner").order_by("-id")
        p = self.request.query_params
        project = p.get("project", "").strip()
        if project.isdigit():
            qs = qs.filter(project_id=int(project))
        owner = p.get("owner", "").strip()
        if owner.isdigit():
            qs = qs.filter(owner_id=int(owner))
        status = p.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(payer_first_name__icontains=search)
                | Q(payer_last_name__icontains=search)
                | Q(payer_username__icontains=search)
                | Q(project__name__icontains=search)
            )
        ordering = p.get("ordering", "").strip()
        if ordering in ("id", "-id", "amount", "-amount", "paid_at", "-paid_at", "created_at", "-created_at"):
            qs = qs.order_by(ordering)
        return qs
