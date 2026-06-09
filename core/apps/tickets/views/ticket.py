from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, mixins

from core.apps.tickets.enums import TicketStatusEnum
from core.apps.tickets.models.ticket import TicketModel
from core.apps.tickets.serializers.ticket import CreateTicketSerializer, TicketSerializer


@extend_schema(tags=["ticket"])
class TicketView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """Foydalanuvchining support murojaatlari: o'zinikini ko'rish va yangi yaratish."""

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = TicketSerializer

    action_serializer_class = {
        "list": TicketSerializer,
        "retrieve": TicketSerializer,
        "create": CreateTicketSerializer,
    }

    def get_queryset(self):
        return TicketModel.objects.filter(user=self.request.user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=TicketStatusEnum.OPEN.value)
