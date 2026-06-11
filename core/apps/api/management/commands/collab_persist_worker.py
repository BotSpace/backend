"""Real-time kollaboratsiya op'larini bazaga saqlovchi worker.

websocket-golang har bir kelgan collab op'ni (binary: msgpack+deflate) Redis
`collab_ops` kanaliga e'lon qiladi: {"project_id", "user_id", "data": base64}.
Bu worker ularni o'qiydi, ochadi va `project.flow`'ga INKREMENTAL yozadi —
loyiha bo'yicha qisqa oynada (FLUSH_INTERVAL) batch qilib, DB yozuvini kamaytirish
uchun. Node-darajali last-write-wins.

Deploy: backend image bilan `python manage.py collab_persist_worker`
(celery-worker kabi alohida deployment).
"""

from __future__ import annotations

import base64
import json
import logging
import time
import zlib
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.apps.api.models import ProjectModel
from core.services.redis_service import client

logger = logging.getLogger(__name__)

CHANNEL = "collab_ops"
FLUSH_INTERVAL = 0.4  # sekund — loyiha bo'yicha op'larni batch qilish oynasi


def _apply_op(nodes: list, edges: list, op: dict) -> None:
    """Bitta op'ni flow (nodes/edges) ga qo'llaydi. Op formati konstruktordagidek:
    {t: nu|nm|na|nd|ea|ed, ...}."""
    t = op.get("t")
    if t == "nu":  # node data yangilash
        for n in nodes:
            if n.get("id") == op.get("id"):
                n["data"] = op.get("data")
                break
    elif t == "nm":  # node ko'chirish
        pos = op.get("position")
        for n in nodes:
            if n.get("id") == op.get("id"):
                n["position"] = pos
                n["positionAbsolute"] = pos
                break
    elif t == "na":  # node qo'shish
        node = op.get("node") or {}
        nid = node.get("id")
        if nid and not any(n.get("id") == nid for n in nodes):
            nodes.append(node)
    elif t == "nd":  # node o'chirish (+ bog'liq edge'lar)
        nid = op.get("id")
        nodes[:] = [n for n in nodes if n.get("id") != nid]
        edges[:] = [e for e in edges if e.get("source") != nid and e.get("target") != nid]
    elif t == "ea":  # edge qo'shish
        edge = op.get("edge") or {}
        eid = edge.get("id")
        if eid and not any(e.get("id") == eid for e in edges):
            edges.append(edge)
    elif t == "ed":  # edge o'chirish
        eid = op.get("id")
        edges[:] = [e for e in edges if e.get("id") != eid]


def _flush(buffers: dict[int, list]) -> None:
    """Buferdagi op'larni loyiha bo'yicha bitta tranzaksiyada qo'llaydi."""
    for pid, ops in list(buffers.items()):
        if not ops:
            continue
        try:
            with transaction.atomic():
                project = ProjectModel.objects.select_for_update().get(pk=pid)
                flow = project.flow if isinstance(project.flow, dict) else None
                if flow is None:
                    # Kutilmagan format (list/None) — buzmaymiz, o'tkazib yuboramiz.
                    logger.warning("collab_persist: project %s flow dict emas — skip", pid)
                    continue
                nodes = flow.setdefault("nodes", [])
                edges = flow.setdefault("edges", [])
                for op in ops:
                    _apply_op(nodes, edges, op)
                project.flow = flow
                project.save(update_fields=["flow"])
        except ProjectModel.DoesNotExist:
            continue
        except Exception:  # noqa: BLE001
            logger.exception("collab_persist: flush xatosi project=%s", pid)


class Command(BaseCommand):
    help = "Collab op'larini Redis'dan o'qib project.flow'ga inkremental saqlaydi."

    def handle(self, *args, **options):
        sub = client.pubsub()
        sub.subscribe(CHANNEL)
        logger.info("collab_persist_worker ishga tushdi (channel=%s)", CHANNEL)
        buffers: dict[int, list] = defaultdict(list)
        last_flush = time.monotonic()
        while True:
            try:
                msg = sub.get_message(ignore_subscribe_messages=True, timeout=FLUSH_INTERVAL)
            except Exception:  # noqa: BLE001
                logger.exception("collab_persist: redis get_message xatosi")
                time.sleep(1)
                continue
            if msg and msg.get("type") == "message":
                op = self._decode(msg.get("data"))
                if op is not None:
                    pid, body = op
                    buffers[pid].append(body)
            now = time.monotonic()
            if buffers and (now - last_flush) >= FLUSH_INTERVAL:
                _flush(buffers)
                buffers.clear()
                last_flush = now

    @staticmethod
    def _decode(raw):
        """Redis payload {project_id, user_id, data:base64(deflate(msgpack))} → (pid, op)."""
        try:
            import msgpack  # talab: requirements'da msgpack

            payload = json.loads(raw)
            pid = int(payload["project_id"])
            # fflate.deflateSync = RAW deflate (zlib header'siz) → wbits=-15.
            blob = zlib.decompress(base64.b64decode(payload["data"]), -15)
            op = msgpack.unpackb(blob, raw=False)
            if isinstance(op, dict):
                return pid, op
        except Exception:  # noqa: BLE001
            logger.debug("collab_persist: op decode xatosi", exc_info=True)
        return None
