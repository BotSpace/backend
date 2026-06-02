# type: ignore
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.cms.views._common import resolve_project
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import EventTypes, NodeExecutionStatus

logger = logging.getLogger(__name__)


class DebugNodeEventView(APIView):
    """Engine'dan kelgan node-execution debug event'ini qabul qilib, WS orqali project owner'iga yuboradi.

    Auth: engine resource endpoint'i bilan bir xil — `Authorization: Bearer <API_TOKEN>` (JWT),
    DRF IsAuthenticated orqali tekshiriladi.

    POST /api/debug/node-event/
    Body: {
        "project_id": "<uuid|int>",
        "chat_id": 123,
        "node_id": "n1",
        "node_type": "SendTextMessageNode",
        "status": "running|success|error",
        "error": "",
        "ts": 1700000000000
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        project_id = data.get("project_id")
        if not project_id:
            return Response({"detail": "project_id majburiy."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        try:
            schema = NodeExecutionStatus(
                project=project.pk,
                chat_id=int(data.get("chat_id", 0)),
                node_id=str(data.get("node_id", "")),
                node_type=data.get("node_type") or None,
                status=str(data.get("status", "")),
                error=data.get("error") or None,
                ts=int(data["ts"]) if data.get("ts") else None,
            )
            ws_publish(project.owner_id, schema, EventTypes.NODE_EXECUTION)
        except Exception as exc:
            # Engine'ni hech qachon bloklamaymiz — faqat log.
            logger.error("DebugNodeEventView ws_publish error: %s", exc)

        return Response({"ok": True})
