"""MongoDB index lifecycle driven by the cms schema."""

from __future__ import annotations

from typing import Any

import pymongo

from core.apps.cms.enums import IndexKind
from core.apps.cms.services.mongo import _coll


def _index_name(field_name: str, kind: str) -> str:
    return f"cms_{field_name}_{kind}"


def ensure_indexes(project_id: int, collection_name: str, fields: list[dict[str, Any]]) -> list[str]:
    """Apply the desired index set for a collection.

    `fields` items are plain dicts with keys: name, kind, index, validators.
    Returns the list of index names ensured.
    """
    c = _coll(project_id, collection_name)
    existing = {ix["name"] for ix in c.list_indexes()}
    created: list[str] = []
    for f in fields:
        ix = f.get("index") or IndexKind.NONE
        name = _index_name(f["name"], ix)
        if ix == IndexKind.NONE:
            continue
        if name in existing:
            created.append(name)
            continue
        rules = f.get("validators") or {}
        if ix == IndexKind.ASC:
            c.create_index([(f["name"], pymongo.ASCENDING)], name=name)
        elif ix == IndexKind.DESC:
            c.create_index([(f["name"], pymongo.DESCENDING)], name=name)
        elif ix == IndexKind.TEXT:
            c.create_index([(f["name"], pymongo.TEXT)], name=name)
        elif ix == IndexKind.HASHED:
            c.create_index([(f["name"], pymongo.HASHED)], name=name)
        elif ix == IndexKind.UNIQUE:
            c.create_index([(f["name"], pymongo.ASCENDING)], name=name, unique=True)
        elif ix == IndexKind.TTL:
            ttl = int(rules.get("ttl_seconds", 0))
            if ttl > 0:
                c.create_index(
                    [(f["name"], pymongo.ASCENDING)],
                    name=name,
                    expireAfterSeconds=ttl,
                )
        created.append(name)
    # Soft-delete helper index (single, idempotent)
    if "cms_deleted_at" not in existing:
        c.create_index([("_deleted_at", pymongo.ASCENDING)], name="cms_deleted_at")
        created.append("cms_deleted_at")
    return created


def drop_field_indexes(project_id: int, collection_name: str, field_name: str) -> None:
    c = _coll(project_id, collection_name)
    for ix in c.list_indexes():
        if ix.get("name", "").startswith(f"cms_{field_name}_"):
            c.drop_index(ix["name"])
