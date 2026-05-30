# type: ignore
"""Admin audit log — paginated, filterable read-only view."""

from rest_framework import mixins, viewsets
from rest_framework import serializers as drf_serializers

from core.apps.administration.models import AdminAuditLogModel
from core.apps.administration.permissions import IsAdminUser


class _AuditLogSerializer(drf_serializers.ModelSerializer):
    actor_phone = drf_serializers.CharField(source="actor.phone", read_only=True, default=None)

    class Meta:
        model = AdminAuditLogModel
        fields = (
            "id",
            "actor",
            "actor_phone",
            "action",
            "target_type",
            "target_id",
            "payload_before",
            "payload_after",
            "ip_address",
            "note",
            "created_at",
        )
        read_only_fields = fields


class AdminAuditLogView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = _AuditLogSerializer

    def get_queryset(self):
        qs = AdminAuditLogModel.objects.select_related("actor").order_by("-id")
        params = self.request.query_params
        if params.get("action"):
            qs = qs.filter(action__icontains=params["action"].strip())
        if params.get("target_type"):
            qs = qs.filter(target_type__iexact=params["target_type"].strip())
        if params.get("target_id"):
            qs = qs.filter(target_id=params["target_id"].strip())
        if params.get("actor"):
            qs = qs.filter(actor_id=params["actor"].strip())
        return qs
