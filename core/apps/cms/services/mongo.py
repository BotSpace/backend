"""Thin wrapper over the existing cms MongoDBClient.

We don't re-implement connection pooling — the original `cms.services.mongo`
already gives us a per-project DB. We only wrap typical CRUD with timestamps,
versioning and soft-delete filtering.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from bson import ObjectId

from core.apps.cms.services.mongo import MongoDBClient


_client_singleton: MongoDBClient | None = None


def get_mongo_client() -> MongoDBClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = MongoDBClient()
    return _client_singleton


def _coll(project_id: int, name: str):
    return get_mongo_client().get_project_database(project_id)[name]


def _stamp_create(doc: dict[str, Any]) -> dict[str, Any]:
    now = dt.datetime.utcnow()
    doc.setdefault("_created_at", now)
    doc.setdefault("_updated_at", now)
    doc.setdefault("_version", 1)
    doc.setdefault("_deleted_at", None)
    return doc


def _stamp_update(patch: dict[str, Any]) -> dict[str, Any]:
    patch.setdefault("_updated_at", dt.datetime.utcnow())
    return patch


def _serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, dt.datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _alive_filter(filter: dict[str, Any] | None, include_deleted: bool) -> dict[str, Any]:
    f = dict(filter or {})
    if include_deleted:
        return f
    f["_deleted_at"] = None
    return f


def _coerce_id(filter: dict[str, Any]) -> dict[str, Any]:
    f = dict(filter)
    if "_id" in f and isinstance(f["_id"], str):
        try:
            f["_id"] = ObjectId(f["_id"])
        except Exception:
            pass
    return f


# ── CRUD ────────────────────────────────────────────────────────────────────


def insert_one(project_id: int, collection: str, document: dict[str, Any]) -> str:
    res = _coll(project_id, collection).insert_one(_stamp_create(dict(document)))
    return str(res.inserted_id)


def insert_many(project_id: int, collection: str, documents: list[dict[str, Any]]) -> list[str]:
    docs = [_stamp_create(dict(d)) for d in documents]
    if not docs:
        return []
    res = _coll(project_id, collection).insert_many(docs)
    return [str(x) for x in res.inserted_ids]


def find_one(
    project_id: int,
    collection: str,
    filter: dict[str, Any],
    *,
    include_deleted: bool = False,
) -> dict[str, Any] | None:
    f = _alive_filter(_coerce_id(filter), include_deleted)
    doc = _coll(project_id, collection).find_one(f)
    return _serialize(doc)


def find(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any] | None = None,
    sort: list[tuple[str, int]] | None = None,
    limit: int = 50,
    skip: int = 0,
    projection: dict[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    f = _alive_filter(_coerce_id(filter or {}), include_deleted)
    cursor = _coll(project_id, collection).find(f, projection=projection)
    if sort:
        cursor = cursor.sort(sort)
    cursor = cursor.skip(skip).limit(limit)
    return [_serialize(d) or {} for d in cursor]


def count(
    project_id: int,
    collection: str,
    filter: dict[str, Any] | None = None,
    *,
    include_deleted: bool = False,
) -> int:
    f = _alive_filter(_coerce_id(filter or {}), include_deleted)
    return _coll(project_id, collection).count_documents(f)


def update_one(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any],
    update: dict[str, Any],
    expected_version: int | None = None,
) -> dict[str, Any]:
    """Optimistic concurrency-aware update.

    If `expected_version` is supplied, the document is updated only if its
    current `_version` matches; the version is then incremented.
    """
    f = _alive_filter(_coerce_id(filter), include_deleted=False)
    if expected_version is not None:
        f["_version"] = expected_version

    if any(k.startswith("$") for k in update):
        ops = dict(update)
        ops.setdefault("$set", {})
        ops["$set"] = _stamp_update(dict(ops["$set"]))
    else:
        ops = {"$set": _stamp_update(dict(update))}
    ops["$inc"] = {**ops.get("$inc", {}), "_version": 1}

    res = _coll(project_id, collection).update_one(f, ops)
    return {"matched": res.matched_count, "modified": res.modified_count}


def update_many(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any],
    update: dict[str, Any],
) -> dict[str, Any]:
    f = _alive_filter(_coerce_id(filter), include_deleted=False)
    if any(k.startswith("$") for k in update):
        ops = dict(update)
        ops.setdefault("$set", {})
        ops["$set"] = _stamp_update(dict(ops["$set"]))
    else:
        ops = {"$set": _stamp_update(dict(update))}
    ops["$inc"] = {**ops.get("$inc", {}), "_version": 1}
    res = _coll(project_id, collection).update_many(f, ops)
    return {"matched": res.matched_count, "modified": res.modified_count}


def soft_delete(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any],
    many: bool = False,
) -> int:
    f = _alive_filter(_coerce_id(filter), include_deleted=False)
    ops = {"$set": {"_deleted_at": dt.datetime.utcnow()}}
    c = _coll(project_id, collection)
    res = c.update_many(f, ops) if many else c.update_one(f, ops)
    return res.modified_count


def restore(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any],
    many: bool = False,
) -> int:
    f = _coerce_id(filter)
    f["_deleted_at"] = {"$ne": None}
    ops = {"$set": {"_deleted_at": None}}
    c = _coll(project_id, collection)
    res = c.update_many(f, ops) if many else c.update_one(f, ops)
    return res.modified_count


def hard_delete(
    project_id: int,
    collection: str,
    *,
    filter: dict[str, Any],
    many: bool = False,
) -> int:
    f = _coerce_id(filter)
    c = _coll(project_id, collection)
    res = c.delete_many(f) if many else c.delete_one(f)
    return res.deleted_count


def aggregate(
    project_id: int,
    collection: str,
    pipeline: list[dict[str, Any]],
    *,
    limit: int = 500,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    # Inject soft-delete filter as first stage unless caller asked otherwise.
    pipe = list(pipeline)
    if not include_deleted and not (pipe and "$match" in pipe[0] and "_deleted_at" in pipe[0]["$match"]):
        pipe = [{"$match": {"_deleted_at": None}}, *pipe]
    out: list[dict[str, Any]] = []
    for doc in _coll(project_id, collection).aggregate(pipe):
        out.append(_serialize(doc) or {})
        if len(out) >= limit:
            break
    return out


def distinct(
    project_id: int,
    collection: str,
    key: str,
    filter: dict[str, Any] | None = None,
) -> list[Any]:
    f = _alive_filter(_coerce_id(filter or {}), include_deleted=False)
    return _coll(project_id, collection).distinct(key, f)


def drop_collection(project_id: int, collection: str) -> None:
    _coll(project_id, collection).drop()
