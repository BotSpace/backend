# type: ignore
"""Audit-log helper. Call this from every admin endpoint after the change
commits — both successful and noteworthy rejected actions can be recorded."""

from __future__ import annotations

import logging
from typing import Any

from core.apps.administration.models import AdminAuditLogModel

logger = logging.getLogger(__name__)


def _client_ip(request) -> str | None:
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def log_admin_action(
    *,
    actor,
    action: str,
    target=None,
    target_type: str | None = None,
    target_id: Any = None,
    before: dict | None = None,
    after: dict | None = None,
    note: str = "",
    request=None,
) -> AdminAuditLogModel | None:
    """Record a destructive admin action.

    Either pass the `target` Django model instance (the helper pulls
    type + id) or supply `target_type` / `target_id` directly.

    Never raises — audit-log failure must not break the actual admin
    operation. Returns the created row, or None on error.
    """
    try:
        if target is not None and target_type is None:
            target_type = type(target).__name__
        if target is not None and target_id is None:
            target_id = getattr(target, "pk", None)
        return AdminAuditLogModel.objects.create(
            actor=actor,
            action=action,
            target_type=(target_type or "")[:60],
            target_id=str(target_id or "")[:60],
            payload_before=before,
            payload_after=after,
            ip_address=_client_ip(request),
            note=note[:255],
        )
    except Exception:  # noqa: BLE001
        logger.exception("admin audit log write failed (action=%s)", action)
        return None
