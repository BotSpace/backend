"""High-level schema service — read/build the field list for a collection,
with Redis caching."""

from __future__ import annotations

from typing import Any

from core.apps.cms.models import Collection, Field
from core.apps.cms.services.cache import (
    get_cached_schema,
    invalidate_schema,
    set_cached_schema,
)


def schema_dict_for(collection: Collection) -> dict[str, Any]:
    return {
        "id": collection.id,
        "project": collection.project_id,
        "name": collection.name,
        "label": collection.label,
        "description": collection.description,
        "system": collection.system,
        "schema_version": collection.schema_version,
        "fields": [_field_to_dict(f) for f in collection.fields.all()],
    }


def _field_to_dict(field: Field) -> dict[str, Any]:
    return {
        "id": field.id,
        "name": field.name,
        "label": field.label,
        "kind": field.kind,
        "required": field.required,
        "default": field.default,
        "validators": field.validators or {},
        "index": field.index,
        "cascade": field.cascade,
        "relation_collection": field.relation_collection_id,
        "order": field.order,
    }


def get_schema(project_id: int, name: str, *, use_cache: bool = True) -> dict[str, Any] | None:
    if use_cache:
        cached = get_cached_schema(project_id, name)
        if cached:
            return cached
    coll = (
        Collection.objects.filter(project_id=project_id, name=name, deleted_at__isnull=True)
        .prefetch_related("fields")
        .first()
    )
    if coll is None:
        return None
    schema = schema_dict_for(coll)
    set_cached_schema(project_id, name, schema)
    return schema


def invalidate(project_id: int, name: str) -> None:
    invalidate_schema(project_id, name)
