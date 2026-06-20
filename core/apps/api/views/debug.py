# type: ignore
import json
import logging

from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.cms.views._common import resolve_project
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import ContextSnapshot, ErrorEvent, EventTypes, NodeExecutionStatus

logger = logging.getLogger(__name__)

# Context snapshot'ni Redis'da saqlaymiz: constructor keyin ulanganda oxirgi holatni olsin.
# TTL: faol debug sessiya davomida (max 10 daqiqa) yangilanib turadi.
_CONTEXT_CACHE_TTL = 600  # sekund

# Per-project chat_id SET: qaysi chatlar uchun snapshot borligini eslab qolish.
# TTL uzunroq — foydalanuvchi refresh qilganda ro'yxat yo'qolmasligi kerak.
_CHATS_SET_TTL = 86400  # 24 soat
_CHATS_CAP = 50  # proyekt bo'yicha saqlanadigam maksimal chat soni


def _context_cache_key(project_pk: int, chat_id: int) -> str:
    return f"debug_ctx_{project_pk}_{chat_id}"


def _chats_set_cache_key(project_pk: int) -> str:
    return f"debug_ctx_chats_{project_pk}"


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

            # Per-project chat_id SET: refresh'da barcha chatlarni topish uchun.
            chats_key = _chats_set_cache_key(project.pk)
            existing_raw = cache.get(chats_key)
            chats_list: list = json.loads(existing_raw) if existing_raw else []
            if chat_id not in chats_list:
                chats_list.append(chat_id)
                if len(chats_list) > _CHATS_CAP:
                    chats_list = chats_list[-_CHATS_CAP:]
            cache.set(chats_key, json.dumps(chats_list), timeout=_CHATS_SET_TTL)
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
            raw = cache.get(_context_cache_key(project.pk, chat_id))
            if raw is None:
                return Response({"snapshot": None})
            return Response({"snapshot": json.loads(raw)})
        except Exception as exc:
            logger.error("DebugContextLatestView cache.get xatosi: %s", exc)
            return Response({"detail": "Cache xatosi."}, status=500)


class DebugContextListView(APIView):
    """Constructor uchun: project bo'yicha barcha faol chatlarning oxirgi snapshot'larini qaytaradi.

    GET /api/debug/context/?project_id=<id>
    Auth: JWT — faqat project owner.
    Javob: {chats: [{chat_id, variables, ts, project}, ...]} — TTL o'tgan chatlar o'tkazib yuboriladi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"detail": "project_id majburiy."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        if project.owner_id != request.user.pk:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        try:
            chats_key = _chats_set_cache_key(project.pk)
            chats_raw = cache.get(chats_key)
            chat_ids: list = json.loads(chats_raw) if chats_raw else []
        except Exception as exc:
            logger.error("DebugContextListView chats_set cache.get xatosi: %s", exc)
            return Response({"detail": "Cache xatosi."}, status=500)

        chats = []
        for cid in chat_ids:
            try:
                snap_raw = cache.get(_context_cache_key(project.pk, cid))
                if snap_raw is None:
                    # TTL o'tgan — o'tkazib yuboramiz
                    continue
                chats.append(json.loads(snap_raw))
            except Exception as exc:
                logger.warning("DebugContextListView snapshot o'qish xatosi chat_id=%s: %s", cid, exc)

        # Eng yangi (ts bo'yicha) birinchi
        chats.sort(key=lambda s: s.get("ts") or 0, reverse=True)

        return Response({"chats": chats})


# ---------------------------------------------------------------------------
# Flow error observability
# ---------------------------------------------------------------------------

_ERRORS_CACHE_TTL = 86400  # 24 soat
_ERRORS_CAP = 100  # project bo'yicha saqlanadigan maksimal xato soni


def _errors_cache_key(project_pk: int) -> str:
    return f"proj_errors_{project_pk}"


class DebugErrorEventView(APIView):
    """Engine'dan kelgan flow xatosini qabul qilib, Redis'ga saqlaydi va WS orqali constructor'ga uzatadi.

    Auth: X-Internal-Token == settings.INTERNAL_API_TOKEN (node-event bilan bir xil).
    Engine yuboradi: {project_id, chat_id, node_id, node_type, message, detail, ts}

    WS event: {event: "error", data: {project, chat_id, node_id, node_type, message, detail, ts}}
    Redis:    proj_errors_{project.pk} — oxirgi 100 ta xato (JSON list), TTL 24h.
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

        message = data.get("message") or ""
        if not message:
            return Response({"detail": "message majburiy."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        ts = int(data["ts"]) if data.get("ts") else None

        error_payload = {
            "project": project.pk,
            "chat_id": int(data.get("chat_id", 0)),
            "node_id": data.get("node_id") or None,
            "node_type": data.get("node_type") or None,
            "message": message,
            "detail": data.get("detail") or None,
            "ts": ts,
        }

        # Redis ro'yxatiga qo'shamiz (cap=100, TTL=24h).
        try:
            key = _errors_cache_key(project.pk)
            existing_raw = cache.get(key)
            errors_list = json.loads(existing_raw) if existing_raw else []
            errors_list.append(error_payload)
            if len(errors_list) > _ERRORS_CAP:
                errors_list = errors_list[-_ERRORS_CAP:]
            cache.set(key, json.dumps(errors_list), timeout=_ERRORS_CACHE_TTL)
        except Exception as exc:
            logger.warning("DebugErrorEventView cache xatosi: %s", exc)

        # WS orqali real-time constructor'ga yuborish.
        try:
            schema = ErrorEvent(
                project=project.pk,
                chat_id=int(data.get("chat_id", 0)),
                node_id=data.get("node_id") or None,
                node_type=data.get("node_type") or None,
                message=message,
                detail=data.get("detail") or None,
                ts=ts,
            )
            ws_publish(project.owner_id, schema, EventTypes.ERROR)
        except Exception as exc:
            logger.error("DebugErrorEventView ws_publish xatosi: %s", exc)

        return Response({"ok": True})


class DebugErrorListView(APIView):
    """Constructor va AI agent uchun: project bo'yicha oxirgi xatolar ro'yxati.

    GET /api/debug/errors/?project_id=<id>&limit=<n>
    Auth: JWT — faqat project owner.
    Javob: {errors: [...]} — eng yangi birinchi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"detail": "project_id majburiy."}, status=400)

        project = resolve_project(project_id)
        if project is None:
            return Response({"detail": "Project topilmadi."}, status=404)

        if project.owner_id != request.user.pk:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        try:
            limit_raw = request.query_params.get("limit")
            limit = int(limit_raw) if limit_raw else _ERRORS_CAP
            limit = max(1, min(limit, _ERRORS_CAP))
        except (ValueError, TypeError):
            limit = _ERRORS_CAP

        try:
            key = _errors_cache_key(project.pk)
            raw = cache.get(key)
            errors_list = json.loads(raw) if raw else []
            # Eng yangi birinchi (oxirgi qo'shilganlar tepada).
            errors_list = list(reversed(errors_list[-limit:]))
        except Exception as exc:
            logger.error("DebugErrorListView cache xatosi: %s", exc)
            return Response({"detail": "Cache xatosi."}, status=500)

        return Response({"errors": errors_list})
