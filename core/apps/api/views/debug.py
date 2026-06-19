# type: ignore
import logging

from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.cms.views._common import resolve_project
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import ContextSnapshot, EventTypes, NodeExecutionStatus

logger = logging.getLogger(__name__)

# Context snapshot'ni Redis'da saqlaymiz: constructor keyin ulanganda oxirgi holatni olsin.
# TTL: faol debug sessiya davomida (max 10 daqiqa) yangilanib turadi.
_CONTEXT_CACHE_TTL = 600  # sekund


def _context_cache_key(project_pk: int, chat_id: int) -> str:
    return f"debug_ctx_{project_pk}_{chat_id}"


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


class DebugContextEventView(APIView):
    """Engine'dan kelgan flow context snapshot'ini qabul qilib, WS orqali constructor'ga uzatadi.

    Auth: X-Internal-Token == settings.INTERNAL_API_TOKEN (node-event bilan bir xil).
    Engine yuboradi: {project_id, chat_id, variables: {...}, ts}

    WS event turi: "context"  →  {event: "context", data: {project, chat_id, variables, ts}}

    Qo'shimcha: oxirgi snapshot Redis'da chat_id bo'yicha 600s saqlanadi.
    Constructor keyinroq ulanganda GET /api/debug/context/?project_id=&chat_id= orqali olishi mumkin.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
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

        chat_id = int(data.get("chat_id", 0))
        variables = data.get("variables") or {}
        ts = int(data["ts"]) if data.get("ts") else None

        # Oxirgi snapshot'ni Redis'da saqlash (constructor keyin ochsa ko'rsin).
        try:
            import json as _json

            snapshot_payload = {"project": project.pk, "chat_id": chat_id, "variables": variables, "ts": ts}
            cache.set(_context_cache_key(project.pk, chat_id), _json.dumps(snapshot_payload), timeout=_CONTEXT_CACHE_TTL)
        except Exception as exc:
            logger.warning("DebugContextEventView cache.set xatosi: %s", exc)

        try:
            schema = ContextSnapshot(
                project=project.pk,
                chat_id=chat_id,
                variables=variables,
                ts=ts,
            )
            ws_publish(project.owner_id, schema, EventTypes.CONTEXT_SNAPSHOT)
        except Exception as exc:
            logger.error("DebugContextEventView ws_publish error: %s", exc)

        return Response({"ok": True})


class DebugContextLatestView(APIView):
    """Constructor uchun: oxirgi saqlangan context snapshot'ni qaytaradi.

    GET /api/debug/context/?project_id=<id>&chat_id=<id>
    Auth: oddiy DRF (JWT) — faqat project owner ko'ra olishi kerak.
    """

    def get(self, request):
        project_id = request.query_params.get("project_id")
        chat_id_raw = request.query_params.get("chat_id")

        if not project_id or not chat_id_raw:
            return Response({"detail": "project_id va chat_id majburiy."}, status=400)

        try:
            chat_id = int(chat_id_raw)
        except (ValueError, TypeError):
            return Response({"detail": "chat_id butun son bo'lishi kerak."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        if project.owner_id != request.user.pk:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        try:
            import json as _json

            raw = cache.get(_context_cache_key(project.pk, chat_id))
            if raw is None:
                return Response({"snapshot": None})
            return Response({"snapshot": _json.loads(raw)})
        except Exception as exc:
            logger.error("DebugContextLatestView cache.get xatosi: %s", exc)
            return Response({"detail": "Cache xatosi."}, status=500)
