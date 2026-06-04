from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.apps.cms.models import Webhook
from core.apps.cms.serializers import WebhookSerializer

from ._common import get_collection_or_404


@extend_schema(tags=["cms"])
class WebhookViewSet(ModelViewSet):
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        coll = get_collection_or_404(
            project_id=self.kwargs["project_id"],
            name=self.kwargs["collection_name"],
            user=self.request.user,
        )
        return Webhook.objects.filter(collection=coll).order_by("-created_at")

    def perform_create(self, serializer):
        coll = get_collection_or_404(
            project_id=self.kwargs["project_id"],
            name=self.kwargs["collection_name"],
            user=self.request.user,
        )
        serializer.save(collection=coll)
