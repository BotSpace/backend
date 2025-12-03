from django_core.mixins import BaseViewSetMixin
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from core.apps.api.models.message import MessageModel
from core.apps.api.serializers import SendMessageSerializer, MessageSerializer


class MessageView(BaseViewSetMixin, ModelViewSet):
    """ViewSet for managing broadcast messages"""
    queryset = MessageModel.objects.all()
    serializer_class = SendMessageSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    action_serializer_class = {
        "list": MessageSerializer,
        "retrieve": MessageSerializer,
        "create": SendMessageSerializer,
        "update": SendMessageSerializer,
        "partial_update": SendMessageSerializer,
    }

    def get_queryset(self):
        """Filter messages by project if provided"""
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project')
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        return queryset.order_by('-id')
