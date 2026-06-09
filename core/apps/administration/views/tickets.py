# type: ignore
"""Admin support tickets — list/retrieve user tickets and reply/close them."""

from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.services import log_admin_action
from core.apps.tickets.enums import TicketStatusEnum
from core.apps.tickets.models.ticket import TicketModel


class AdminTicketSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = TicketModel
        fields = [
            "id",
            "user",
            "user_phone",
            "subject",
            "message",
            "status",
            "admin_reply",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminTicketReplySerializer(serializers.Serializer):
    admin_reply = serializers.CharField(allow_blank=True, required=False, default="")
    status = serializers.ChoiceField(choices=TicketStatusEnum.choices, required=False)


class AdminTicketsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTicketSerializer

    def get_queryset(self):
        qs = TicketModel.objects.select_related("user").order_by("-id")
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["patch"])
    def reply(self, request, pk=None):
        serializer = AdminTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = self.get_queryset().get(pk=pk)
        before = {"status": target.status}
        reply = serializer.validated_data.get("admin_reply", "")
        if reply:
            target.admin_reply = reply
        new_status = serializer.validated_data.get("status")
        target.status = new_status or TicketStatusEnum.PENDING.value
        target.save(update_fields=["admin_reply", "status", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="ticket.reply",
            target=target,
            before=before,
            after={"status": target.status},
            note=reply[:255],
            request=request,
        )
        target.refresh_from_db()
        return Response(self.get_serializer(target).data, status=status.HTTP_200_OK)
