"""Health-check endpoints used by load balancers and uptime monitors."""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.db import connections
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


def _check_database() -> Dict[str, Any]:
    try:
        connections["default"].ensure_connection()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001 — surface any DB failure
        logger.warning("health: database down: %s", exc)
        return {"status": "down", "error": exc.__class__.__name__}


def _check_redis() -> Dict[str, Any]:
    try:
        from django.core.cache import cache

        cache.set("__health__", "1", timeout=5)
        if cache.get("__health__") != "1":
            return {"status": "degraded"}
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("health: redis down: %s", exc)
        return {"status": "down", "error": exc.__class__.__name__}


def _check_mongo() -> Dict[str, Any]:
    try:
        from core.apps.cms.services.mongo import MongoDBClient

        client = MongoDBClient()
        try:
            client.client.admin.command("ping")
            return {"status": "ok"}
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("health: mongo down: %s", exc)
        return {"status": "down", "error": exc.__class__.__name__}


@api_view(["GET"])
@permission_classes([AllowAny])
def liveness(_request):
    """Process is alive — used by Kubernetes liveness probe."""
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness(_request):
    """All critical dependencies (DB, Redis, Mongo) reachable — readiness probe."""
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "mongo": _check_mongo(),
    }
    ok = all(c.get("status") == "ok" for c in checks.values())
    response = JsonResponse({"status": "ok" if ok else "degraded", "checks": checks})
    response.status_code = 200 if ok else 503
    return response
