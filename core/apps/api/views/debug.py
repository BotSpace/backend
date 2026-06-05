# type: ignore
import logging

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.cms.views._common import resolve_project
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import EventTypes, NodeExecutionStatus

logger = logging.getLogger(__name__)


class DebugNodeEventView(APIView):
    """Engine'dan kelgan node-execution debug event'ini qabul qilib, WS orqali project owner'iga yuboradi.

    Auth: shared X-Internal-Token (subscription.report_usage / template internal bilan bir xil).
    Engine `X-Internal-Token: <DEBUG_EVENT_TOKEN>` (== settings.INTERNAL_API_TOKEN) yuboradi.

    POST /api/debug/node-event/
    Body: {project_id, chat_id, node_id, node_type, status, error, ts}
    """

    # Skip global DRF authentication: the project-wide InternalToken auth
    # intercepts any X-Internal-Token and demands an X-User-Id header (401).
    # The engine has no user — we authenticate manually below.
    authentication_classes = []
    permission_classes = [AllowAny]
    # Ichki endpoint (X-Internal-Token) — global anon throttle (60/min/IP) bu yerda
    # MUTLAQO yaroqsiz: bitta faol debug sessiya minutiga o'nlab event yuboradi va
    # limit tugagach eventlar 429 bilan yo'qolib, paneldagi node statuslar "o'lib"
    # qolardi. Auth tokeni tekshiriladi, throttle kerak emas.
    throttle_classes = []

    def post(self, request):
        expected = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not expected or request.headers.get("X-Internal-Token", "") != expected:
            return Response({"detail": "Ruxsat etilmagan so'rov."}, status=403)

        data = request.data
        project_id = data.get("project_id")
        if not project_id:
            return Response({"detail": "project_id majburiy."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        # Keepalive: node event = foydalanuvchi debug bot bilan FAOL ishlayapti.
        # sync_debug 10 daqiqa updated_at yangilanmagan containerlarni o'chiradi —
        # faol sessiya o'chib ketmasligi uchun updated_at'ni yangilab turamiz.
        # Har eventda emas (burst'da DB urilmasin) — cache bilan 60s throttle.
        try:
            from django.core.cache import cache

            if cache.add(f"debug_touch_{project.pk}", 1, timeout=60):
                from django.utils import timezone

                from core.apps.api.models.project import DebugModel

                DebugModel.objects.filter(project=project).update(updated_at=timezone.now())
        except Exception as exc:
            logger.warning("DebugNodeEventView keepalive xatosi: %s", exc)

        try:
            schema = NodeExecutionStatus(
                project=project.pk,
                chat_id=int(data.get("chat_id", 0)),
                node_id=str(data.get("node_id", "")),
                node_type=data.get("node_type") or None,
                status=str(data.get("status", "")),
                error=data.get("error") or None,
                ts=int(data["ts"]) if data.get("ts") else None,
                run_id=int(data["run_id"]) if data.get("run_id") else None,
                seq=int(data["seq"]) if data.get("seq") else None,
            )
            ws_publish(project.owner_id, schema, EventTypes.NODE_EXECUTION)
        except Exception as exc:
            # Engine'ni hech qachon bloklamaymiz — faqat log.
            logger.error("DebugNodeEventView ws_publish error: %s", exc)

        return Response({"ok": True})
