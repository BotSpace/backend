"""CMS hujjatlari uchun MongoDB CRUD qatlami.

Barcha loyihalar hujjatlari bitta umumiy database'da (`CMS_SHARED_DB`, default
botspace_cms), collection nomi bo'yicha saqlanadi; har hujjatda `_project_id`
maydoni bo'ladi. Har bir so'rov yagona chokepoint'da `_project_id` bilan
filtrlanadi (tenant izolyatsiya), foydalanuvchi filtri shu bilan birga qo'llanadi.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from bson import ObjectId

from config.env import env
from core.apps.cms_legacy.services.mongo import MongoDBClient

# Umumiy CMS database nomi va ichki tenant maydoni.
SHARED_DB_NAME: str = env.str("CMS_SHARED_DB", default="botspace_cms")
TENANT_FIELD = "_project_id"


_client_singleton: MongoDBClient | None = None


def get_mongo_client() -> MongoDBClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = MongoDBClient()
    return _client_singleton


def _coll(project_id: int, name: str):
    """Yagona chokepoint — umumiy DB'dagi collection. BARCHA tenant'larnikini
    saqlaydi, shuning uchun so'rovlar `_scoped()`/`_tenant()` bilan filtrlanishi SHART."""
    return get_mongo_client().client[SHARED_DB_NAME][name]


def _tenant(project_id: int, filter: dict[str, Any]) -> dict[str, Any]:
    """Filtrga `_project_id` ni majburiy qo'shadi (tenant izolyatsiya)."""
    filter[TENANT_FIELD] = project_id
    return filter


def _scoped(project_id: int, filter: dict[str, Any] | None, *, include_deleted: bool = False) -> dict[str, Any]:
    """Yagona filtr quruvchi: _id coerce + soft-delete + tenant scoping.
    BARCHA o'qish/update/delete funksiyalari shuni ishlatadi."""
    return _tenant(project_id, _alive_filter(_coerce_id(filter or {}), include_deleted))


def _stamp_create(doc: dict[str, Any], project_id: int) -> dict[str, Any]:
    now = dt.datetime.utcnow()
    doc.setdefault("_created_at", now)
    doc.setdefault("_updated_at", now)
    doc.setdefault("_version", 1)
    doc.setdefault("_deleted_at", None)
    doc[TENANT_FIELD] = project_id
    return doc


def _stamp_update(patch: dict[str, Any]) -> dict[str, Any]:
    patch.setdefault("_updated_at", dt.datetime.utcnow())
    return patch


def _serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if k == TENANT_FIELD:  # ichki tenant maydoni API'da ko'rinmaydi
            continue
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
    res = _coll(project_id, collection).insert_one(_stamp_create(dict(document), project_id))
    return str(res.inserted_id)


def insert_many(project_id: int, collection: str, documents: list[dict[str, Any]]) -> list[str]:
    docs = [_stamp_create(dict(d), project_id) for d in documents]
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
    f = _scoped(project_id, filter, include_deleted=include_deleted)
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
    after_id: str | None = None,
) -> list[dict[str, Any]]:
    """Hujjatlarni qaytaradi.

    `after_id` berilsa — kursor (cursor) paginatsiya: `_id` bo'yicha o'sish
    tartibida, berilgan `_id`'dan KEYINGI hujjatlardan boshlanadi (minglab
    hujjatli relation tanlovida "pastga scroll → keyingisini yukla" uchun).
    Bunda `sort`/`skip` e'tiborga olinmaydi (deterministik `_id` tartibi shart).
    """
    f = _scoped(project_id, filter, include_deleted=include_deleted)
    if after_id:
        try:
            f["_id"] = {"$gt": ObjectId(after_id)}
        except Exception:
            pass
        sort = [("_id", 1)]
        skip = 0
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
    f = _scoped(project_id, filter, include_deleted=include_deleted)
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
    f = _scoped(project_id, filter, include_deleted=False)
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
    f = _scoped(project_id, filter, include_deleted=False)
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
    f = _scoped(project_id, filter, include_deleted=False)
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
    f = _tenant(project_id, _coerce_id(filter))
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
    f = _tenant(project_id, _coerce_id(filter))
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
    # Tenant + soft-delete $match'ni pipeline boshiga MAJBURIY qo'yamiz —
    # boshqa tenant hujjatlarini ko'rishdan saqlaydi.
    match: dict[str, Any] = {TENANT_FIELD: project_id}
    if not include_deleted:
        match["_deleted_at"] = None
    pipe = [{"$match": match}, *pipeline]
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
    f = _scoped(project_id, filter, include_deleted=False)
    return _coll(project_id, collection).distinct(key, f)


def drop_collection(project_id: int, collection: str) -> None:
    # Umumiy collection BARCHA tenant'larniki — DROP qilmaymiz, faqat shu
    # loyihaning hujjatlarini o'chiramiz.
    _coll(project_id, collection).delete_many({TENANT_FIELD: project_id})
