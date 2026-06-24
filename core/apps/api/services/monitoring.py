"""Bot monitoring service — Prometheus + Django DB (disk) metrikalar."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.env import env

logger = logging.getLogger(__name__)

PROMETHEUS_URL: str = env.str(
    "PROMETHEUS_URL",
    default="http://monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090",
)
_PROM_TIMEOUT = 8  # soniya


def prom_query(promql: str) -> float | None:
    """Prometheus instant query. Natija — birinchi sample qiymati yoki None."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=_PROM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if not results:
            return None
        # result[0]["value"] = [timestamp, "value_string"]
        raw = results[0].get("value", [None, None])[1]
        if raw is None:
            return None
        return float(raw)
    except Exception as exc:
        logger.debug("prom_query failed (query=%r): %s", promql, exc)
        return None


def prom_query_range(promql: str, start: float, end: float, step: str) -> list[list[float]]:
    """Prometheus range query. Natija — [[unix_ts, value], ...] (bo'sh bo'lsa []).

    Bir nechta seriya qaytsa, ularni vaqt bo'yicha qo'shadi (sum) — masalan bitta
    loyihaning bir nechta pod'i.
    """
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
            timeout=_PROM_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("data", {}).get("result", [])
        if not results:
            return []
        # Seriyalarni timestamp bo'yicha yig'amiz (bir loyiha = ko'p pod bo'lishi mumkin)
        acc: dict[int, float] = {}
        for series in results:
            for ts, val in series.get("values", []):
                try:
                    acc[int(ts)] = acc.get(int(ts), 0.0) + float(val)
                except (TypeError, ValueError):
                    continue
        return [[float(ts), acc[ts]] for ts in sorted(acc)]
    except Exception as exc:
        logger.debug("prom_query_range failed (query=%r): %s", promql, exc)
        return []


def prom_query_by_pod(promql: str) -> dict[str, float]:
    """`sum by (pod)(...)` instant query. Natija — {pod_name: value}."""
    out: dict[str, float] = {}
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=_PROM_TIMEOUT,
        )
        resp.raise_for_status()
        for series in resp.json().get("data", {}).get("result", []):
            pod = series.get("metric", {}).get("pod")
            raw = series.get("value", [None, None])[1]
            if pod is None or raw is None:
                continue
            try:
                out[pod] = float(raw)
            except (TypeError, ValueError):
                continue
    except Exception as exc:
        logger.debug("prom_query_by_pod failed (query=%r): %s", promql, exc)
    return out


def _pod_regex(project_id: int) -> str:
    return f"(debug|release)-{project_id}-.*"


def fetch_prometheus_metrics(project_id: int) -> tuple[dict[str, float | None], bool]:
    """CPU, memory, network metrikalarini Prometheus'dan oladi.

    Returns:
        (metrics_dict, prometheus_available)
    """
    regex = _pod_regex(project_id)
    ns = "botmother"

    cpu = prom_query(
        f'sum(rate(container_cpu_usage_seconds_total{{namespace="{ns}",pod=~"{regex}",container!=""}}[5m]))'
    )
    memory = prom_query(
        f'sum(container_memory_working_set_bytes{{namespace="{ns}",pod=~"{regex}",container!=""}})'
    )
    net_rx = prom_query(
        f'sum(rate(container_network_receive_bytes_total{{namespace="{ns}",pod=~"{regex}"}}[5m]))'
    )
    net_tx = prom_query(
        f'sum(rate(container_network_transmit_bytes_total{{namespace="{ns}",pod=~"{regex}"}}[5m]))'
    )

    available = any(v is not None for v in (cpu, memory, net_rx, net_tx))
    metrics: dict[str, float | None] = {
        "cpu_cores": cpu,
        "memory_bytes": memory,
        "net_rx_bps": net_rx,
        "net_tx_bps": net_tx,
    }
    return metrics, available


def fetch_disk_metrics(project_id: int) -> dict[str, int]:
    """Loyihaning saqlangan ma'lumoti hajmini DB + MongoDB orqali hisoblaydi."""
    files_bytes = _files_bytes(project_id)
    cms_bytes = _cms_bytes(project_id)
    return {
        "disk_bytes": files_bytes + cms_bytes,
        "disk_files_bytes": files_bytes,
        "disk_cms_bytes": cms_bytes,
    }


def _files_bytes(project_id: int) -> int:
    """Loyihaga yuklab olingan fayllar umumiy hajmi (bytes)."""
    try:
        from django.db.models import Sum
        from core.apps.api.models.file import FileModel

        result = FileModel.objects.filter(project_id=project_id).aggregate(total=Sum("filesize"))
        return int(result["total"] or 0)
    except Exception as exc:
        logger.debug("_files_bytes failed (project=%s): %s", project_id, exc)
        return 0


def _cms_bytes(project_id: int) -> int:
    """Loyihaning MongoDB CMS hujjatlari taxminiy hajmi (bytes).

    Har hujjat uchun `bson.encode` ishlatmay, `bson.BSON` emas, chunki bu import
    qimmat. O'rniga hujjat JSON hajmini taxminiy bayt sifatida hisoblaymiz — eng
    yengil va kutubxonasiz yondashuv. Aniqroq hisoblash uchun `collStats` command
    ham ishlatilishi mumkin, lekin bu klasterdagi har bir collection uchun Mongo
    admin huquqi talab qiladi.
    """
    try:
        import json as _json
        from core.apps.cms.models.collection import Collection
        from core.apps.cms.services.mongo import get_mongo_client, SHARED_DB_NAME, TENANT_FIELD

        collection_names = list(
            Collection.objects.filter(
                project_id=project_id, deleted_at__isnull=True
            ).values_list("name", flat=True)
        )
        if not collection_names:
            return 0

        mongo = get_mongo_client()
        db = mongo.client[SHARED_DB_NAME]
        total = 0
        for name in collection_names:
            try:
                # collStats command — Mongo 4.4+ mavjud, eng to'g'ri usul
                stats = db.command("collStats", name)
                # shu loyiha hissasini proporsional baholash:
                # loyiha hujjatlari / jami hujjatlar * storageSize
                storage_size = int(stats.get("storageSize", 0))
                total_count = int(stats.get("count", 0))
                if total_count == 0:
                    continue
                project_count = db[name].count_documents({TENANT_FIELD: project_id})
                if project_count == 0:
                    continue
                total += int(storage_size * project_count / total_count)
            except Exception:
                # collStats ishlamasa, JSON taxmin:
                try:
                    docs = list(db[name].find({TENANT_FIELD: project_id}, limit=100))
                    sample_bytes = sum(len(_json.dumps(d, default=str).encode()) for d in docs)
                    if docs:
                        project_count = db[name].count_documents({TENANT_FIELD: project_id})
                        avg = sample_bytes / len(docs)
                        total += int(avg * project_count)
                except Exception as inner:
                    logger.debug("_cms_bytes: collection %r failed: %s", name, inner)
        return total
    except Exception as exc:
        logger.debug("_cms_bytes failed (project=%s): %s", project_id, exc)
        return 0


def get_project_monitoring(project_id: int) -> dict[str, Any]:
    """Monitoring uchun to'liq metrikalar to'plami.

    Prometheus ulanmasa — cpu/memory/net null, prometheus_available=False,
    lekin disk (DB) baribir qaytadi.
    """
    prom_metrics, prom_available = fetch_prometheus_metrics(project_id)
    disk_metrics = fetch_disk_metrics(project_id)

    return {
        **prom_metrics,
        **disk_metrics,
        "prometheus_available": prom_available,
    }


# ── Tarix (range) ─────────────────────────────────────────────────────────────

# range_key → (sekund_orqaga, prometheus_step). 10 kun retention bilan mos.
_RANGE_PRESETS: dict[str, tuple[int, str]] = {
    "1h": (3600, "1m"),
    "6h": (6 * 3600, "5m"),
    "24h": (24 * 3600, "15m"),
    "7d": (7 * 24 * 3600, "1h"),
}
DEFAULT_RANGE = "24h"


def _disk_history(project_id: int, since_ts: float) -> list[list[float]]:
    """Snapshot jadvalidan disk tarixini oladi: [[unix_ts, disk_bytes], ...]."""
    try:
        from datetime import datetime, timezone

        from core.apps.api.models.monitoring import ProjectResourceSnapshot

        since = datetime.fromtimestamp(since_ts, tz=timezone.utc)
        rows = (
            ProjectResourceSnapshot.objects.filter(project_id=project_id, created_at__gte=since)
            .order_by("created_at")
            .values_list("created_at", "disk_bytes")
        )
        return [[dt.timestamp(), float(val)] for dt, val in rows]
    except Exception as exc:
        logger.debug("_disk_history failed (project=%s): %s", project_id, exc)
        return []


def get_project_history(project_id: int, range_key: str = DEFAULT_RANGE) -> dict[str, Any]:
    """CPU/RAM/network tarixini Prometheus'dan, disk tarixini snapshot'dan qaytaradi."""
    import time

    seconds, step = _RANGE_PRESETS.get(range_key, _RANGE_PRESETS[DEFAULT_RANGE])
    end = time.time()
    start = end - seconds
    regex = _pod_regex(project_id)
    ns = "botmother"

    cpu = prom_query_range(
        f'sum(rate(container_cpu_usage_seconds_total{{namespace="{ns}",pod=~"{regex}",container!=""}}[5m]))',
        start, end, step,
    )
    memory = prom_query_range(
        f'sum(container_memory_working_set_bytes{{namespace="{ns}",pod=~"{regex}",container!=""}})',
        start, end, step,
    )
    net_rx = prom_query_range(
        f'sum(rate(container_network_receive_bytes_total{{namespace="{ns}",pod=~"{regex}"}}[5m]))',
        start, end, step,
    )
    net_tx = prom_query_range(
        f'sum(rate(container_network_transmit_bytes_total{{namespace="{ns}",pod=~"{regex}"}}[5m]))',
        start, end, step,
    )

    return {
        "range": range_key if range_key in _RANGE_PRESETS else DEFAULT_RANGE,
        "step": step,
        "prometheus_available": any([cpu, memory, net_rx, net_tx]),
        "series": {
            "cpu_cores": cpu,
            "memory_bytes": memory,
            "net_rx_bps": net_rx,
            "net_tx_bps": net_tx,
            "disk_bytes": _disk_history(project_id, start),
        },
    }


# ── Snapshot yig'uvchi (celery beat) ──────────────────────────────────────────


def snapshot_all_projects_disk() -> int:
    """Reliz/debug'i bor har loyihaning disk hajmini snapshot jadvaliga yozadi.

    Returns: yozilgan snapshot soni.
    """
    from core.apps.api.models.monitoring import ProjectResourceSnapshot
    from core.apps.api.models.project import ProjectModel

    # Faqat reliz qilingan loyihalar (bo'sh loyihalar uchun snapshot keraksiz).
    project_ids = list(
        ProjectModel.objects.filter(relases__isnull=False, deleted_at__isnull=True)
        .values_list("id", flat=True)
        .distinct()
    )
    count = 0
    for pid in project_ids:
        try:
            disk = fetch_disk_metrics(pid)
            ProjectResourceSnapshot.objects.create(
                project_id=pid,
                disk_bytes=disk["disk_bytes"],
                disk_files_bytes=disk["disk_files_bytes"],
                disk_cms_bytes=disk["disk_cms_bytes"],
            )
            count += 1
        except Exception as exc:
            logger.warning("snapshot project=%s failed: %s", pid, exc)
    return count


# ── Admin: barcha loyihalar joriy resurs holati ───────────────────────────────


def _project_id_from_pod(pod: str) -> int | None:
    """`debug-12-abc` / `release-12-3-xyz` → 12."""
    import re

    m = re.match(r"^(?:debug|release)-(\d+)-", pod)
    return int(m.group(1)) if m else None


def fetch_current_usage_by_project() -> tuple[dict[int, dict[str, float]], bool]:
    """Butun namespace bo'yicha CPU/RAM'ni bir so'rovda olib, loyiha bo'yicha yig'adi.

    Returns: ({project_id: {"cpu_cores": x, "memory_bytes": y}}, prometheus_available)
    """
    ns = "botmother"
    regex = r"(debug|release)-[0-9]+-.*"
    cpu_by_pod = prom_query_by_pod(
        f'sum by (pod)(rate(container_cpu_usage_seconds_total{{namespace="{ns}",pod=~"{regex}",container!=""}}[5m]))'
    )
    mem_by_pod = prom_query_by_pod(
        f'sum by (pod)(container_memory_working_set_bytes{{namespace="{ns}",pod=~"{regex}",container!=""}})'
    )
    available = bool(cpu_by_pod or mem_by_pod)

    out: dict[int, dict[str, float]] = {}
    for pod, val in cpu_by_pod.items():
        pid = _project_id_from_pod(pod)
        if pid is None:
            continue
        out.setdefault(pid, {"cpu_cores": 0.0, "memory_bytes": 0.0})["cpu_cores"] += val
    for pod, val in mem_by_pod.items():
        pid = _project_id_from_pod(pod)
        if pid is None:
            continue
        out.setdefault(pid, {"cpu_cores": 0.0, "memory_bytes": 0.0})["memory_bytes"] += val
    return out, available


def latest_disk_by_project(project_ids: list[int]) -> dict[int, int]:
    """Berilgan loyihalar uchun eng oxirgi snapshot disk_bytes — {project_id: bytes}."""
    if not project_ids:
        return {}
    try:
        from core.apps.api.models.monitoring import ProjectResourceSnapshot

        out: dict[int, int] = {}
        # Har loyiha uchun eng oxirgi snapshot (DISTINCT ON — Postgres).
        rows = (
            ProjectResourceSnapshot.objects.filter(project_id__in=project_ids)
            .order_by("project_id", "-created_at")
            .distinct("project_id")
            .values_list("project_id", "disk_bytes")
        )
        for pid, val in rows:
            out[pid] = int(val)
        return out
    except Exception as exc:
        logger.debug("latest_disk_by_project failed: %s", exc)
        return {}
