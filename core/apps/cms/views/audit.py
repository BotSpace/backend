from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from core.apps.cms.models import AuditLog
from core.apps.cms.serializers import AuditLogSerializer

from ._common import get_collection_or_404


@extend_schema(tags=["cms"])
class CollectionAuditView(ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        coll = get_collection_or_404(
            project_id=self.kwargs["project_id"],
            name=self.kwargs["collection_name"],
            user=self.request.user,
        )
        qs = AuditLog.objects.filter(collection=coll)
        action_q = self.request.query_params.get("action")
        doc_id = self.request.query_params.get("document_id")
        if action_q:
            qs = qs.filter(action=action_q)
        if doc_id:
            qs = qs.filter(document_id=doc_id)
        return qs.order_by("-created_at")[:200]
