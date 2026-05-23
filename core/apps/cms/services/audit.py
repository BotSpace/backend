"""Audit logging helpers."""

from __future__ import annotations

from typing import Any

from core.apps.cms.enums import AuditAction
from core.apps.cms.models import AuditLog, Collection


def log(
    collection: Collection,
    actor_id: int | None,
    action: AuditAction | str,
    *,
    document_id: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        collection=collection,
        actor_id=actor_id,
        action=str(action),
        document_id=document_id or "",
        before=before,
        after=after,
        meta=meta or {},
    )
