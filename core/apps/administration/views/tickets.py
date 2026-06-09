# type: ignore
"""Admin support tickets — view the conversation, reply (chat), and close."""

from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.services import log_admin_action
from core.apps.tickets.enums import TicketSenderEnum, TicketStatusEnum
from core.apps.tickets.models.ticket import TicketMessageModel, TicketModel
from core.apps.tickets.serializers.ticket import TicketMessageSerializer


class AdminTicketSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = TicketModel
        fields = ["id", "user", "user_phone", "subject", "status", "created_at", "updated_at", "messages"]
        read_only_fields = fields


class AdminTicketReplySerializer(serializers.Serializer):
    message = serializers.CharField()
    attachment = serializers.FileField(required=False, allow_null=True)
    close = serializers.BooleanField(required=False, default=False)


class AdminTicketsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = AdminTicketSerializer

    def get_queryset(self):
        qs = TicketModel.objects.select_related("user").prefetch_related("messages").order_by("-updated_at", "-id")
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, pk=None):
        serializer = AdminTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target = self.get_queryset().get(pk=pk)
        before = {"status": target.status}
        TicketMessageModel.objects.create(
            ticket=target,
            sender=TicketSenderEnum.ADMIN.value,
            author=request.user,
            message=data["message"],
            attachment=data.get("attachment"),
        )
        target.status = (
            TicketStatusEnum.CLOSED.value if data.get("close") else TicketStatusEnum.PENDING.value
        )
        target.save(update_fields=["status", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="ticket.reply",
            target=target,
            before=before,
            after={"status": target.status},
            note=data["message"][:255],
            request=request,
        )
        target.refresh_from_db()
        return Response(self.get_serializer(target).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="close")
    def close(self, request, pk=None):
        target = self.get_queryset().get(pk=pk)
        before = {"status": target.status}
        target.status = TicketStatusEnum.CLOSED.value
        target.save(update_fields=["status", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="ticket.close",
            target=target,
            before=before,
            after={"status": target.status},
            request=request,
        )
        return Response(self.get_serializer(target).data)
