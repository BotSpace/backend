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
