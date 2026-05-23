"""Redis cache for collection schema (per-project, write-through invalidation).

Document-level caching is intentionally avoided — strong consistency matters
for CRM-like flows. Schema caching is safe because schema reads are very hot
(every document write triggers validation) and writes are rare.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.cache import cache


_KEY = "cms:schema:{project}:{name}"
_TTL_SECONDS = 600


def schema_cache_key(project_id: int, name: str) -> str:
    return _KEY.format(project=project_id, name=name)


def get_cached_schema(project_id: int, name: str) -> dict[str, Any] | None:
    raw = cache.get(schema_cache_key(project_id, name))
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw


def set_cached_schema(project_id: int, name: str, schema: dict[str, Any]) -> None:
    cache.set(schema_cache_key(project_id, name), schema, timeout=_TTL_SECONDS)


def invalidate_schema(project_id: int, name: str) -> None:
    cache.delete(schema_cache_key(project_id, name))
