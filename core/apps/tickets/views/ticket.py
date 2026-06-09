from django.db import transaction
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from core.apps.tickets.enums import TicketSenderEnum, TicketStatusEnum
from core.apps.tickets.models.ticket import TicketMessageModel, TicketModel
from core.apps.tickets.serializers.ticket import (
    CreateMessageSerializer,
    CreateTicketSerializer,
    TicketSerializer,
)


@extend_schema(tags=["ticket"])
class TicketView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """Foydalanuvchining support murojaatlari (suhbat ko'rinishida)."""

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = TicketSerializer

    action_serializer_class = {
        "list": TicketSerializer,
        "retrieve": TicketSerializer,
        "create": CreateTicketSerializer,
        "reply": CreateMessageSerializer,
    }

    def get_queryset(self):
        return (
            TicketModel.objects.filter(user=self.request.user)
            .prefetch_related("messages")
            .order_by("-updated_at", "-id")
        )

    def create(self, request, *args, **kwargs):
        serializer = CreateTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            ticket = TicketModel.objects.create(
                user=request.user,
                subject=data["subject"],
                status=TicketStatusEnum.OPEN.value,
            )
            TicketMessageModel.objects.create(
                ticket=ticket,
                sender=TicketSenderEnum.USER.value,
                author=request.user,
                message=data["message"],
                attachment=data.get("attachment"),
            )
        return Response(
            TicketSerializer(ticket, context=self.get_serializer_context()).data,
            status=http_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = CreateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        TicketMessageModel.objects.create(
            ticket=ticket,
            sender=TicketSenderEnum.USER.value,
            author=request.user,
            message=data["message"],
            attachment=data.get("attachment"),
        )
        # Foydalanuvchi yozdi — support javobini kutadi.
        if ticket.status != TicketStatusEnum.OPEN.value:
            ticket.status = TicketStatusEnum.OPEN.value
            ticket.save(update_fields=["status", "updated_at"])
        else:
            ticket.save(update_fields=["updated_at"])
        return Response(
            TicketSerializer(ticket, context=self.get_serializer_context()).data,
            status=http_status.HTTP_201_CREATED,
        )
