from django_core.mixins import BaseViewSetMixin
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models.message import MessageModel
from core.apps.api.serializers import SendMessageSerializer, MessageSerializer


class MessageView(BaseViewSetMixin, ModelViewSet):
    queryset = MessageModel.objects.all()
    serializer_class = SendMessageSerializer
    action_serializer_class = {
        "list": MessageSerializer,
        "create": SendMessageSerializer,
    }

