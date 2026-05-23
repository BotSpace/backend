"""High-level document service — combines validation, mongo, audit, webhook."""

from __future__ import annotations

from typing import Any

from core.apps.cms.enums import AuditAction, WebhookEvent
from core.apps.cms.models import Collection
from core.apps.cms.services import audit, mongo, webhook
from core.apps.cms.services.schema import get_schema
from core.apps.cms.services.validator import ValidationError, validate_document


def _schema_fields(project_id: int, name: str) -> list[dict[str, Any]]:
    schema = get_schema(project_id, name) or {}
    return schema.get("fields") or []


def insert(
    collection: Collection,
    document: dict[str, Any],
    *,
    actor_id: int | None = None,
) -> dict[str, Any]:
    fields = _schema_fields(collection.project_id, collection.name)
    clean = validate_document(fields, document, partial=False)
    inserted_id = mongo.insert_one(collection.project_id, collection.name, clean)
    audit.log(
        collection,
        actor_id,
        AuditAction.CREATE,
        document_id=inserted_id,
        after=clean,
    )
    webhook.fire(collection, WebhookEvent.DOC_CREATED, {"id": inserted_id, "document": clean})
    return {"_id": inserted_id, **clean}


def bulk_insert(
    collection: Collection,
    documents: list[dict[str, Any]],
    *,
    actor_id: int | None = None,
) -> dict[str, Any]:
    fields = _schema_fields(collection.project_id, collection.name)
    cleaned: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for idx, doc in enumerate(documents):
        try:
            cleaned.append(validate_document(fields, doc, partial=False))
        except ValidationError as exc:
            errors.append({"index": idx, "errors": exc.errors})
    if errors:
        raise ValidationError({"bulk": errors})  # type: ignore[arg-type]
    ids = mongo.insert_many(collection.project_id, collection.name, cleaned)
    audit.log(
        collection,
        actor_id,
        AuditAction.BULK_INSERT,
        meta={"count": len(ids)},
    )
    return {"inserted_ids": ids, "count": len(ids)}


def update(
    collection: Collection,
    *,
    document_id: str,
    patch: dict[str, Any],
    expected_version: int | None = None,
    actor_id: int | None = None,
) -> dict[str, Any]:
    fields = _schema_fields(collection.project_id, collection.name)
    clean = validate_document(fields, patch, partial=True)
    before = mongo.find_one(collection.project_id, collection.name, {"_id": document_id})
    res = mongo.update_one(
        collection.project_id,
        collection.name,
        filter={"_id": document_id},
        update=clean,
        expected_version=expected_version,
    )
    if res["matched"] == 0:
        if expected_version is not None:
            raise ValueError(
                "Concurrent update conflict — expected_version did not match"
            )
        raise LookupError("document not found")
    after = mongo.find_one(collection.project_id, collection.name, {"_id": document_id})
    audit.log(
        collection,
        actor_id,
        AuditAction.UPDATE,
        document_id=document_id,
        before=before,
        after=after,
    )
    webhook.fire(collection, WebhookEvent.DOC_UPDATED, {"id": document_id, "before": before, "after": after})
    return after or {}


def soft_delete(
    collection: Collection,
    *,
    document_id: str,
    actor_id: int | None = None,
) -> bool:
    before = mongo.find_one(collection.project_id, collection.name, {"_id": document_id})
    modified = mongo.soft_delete(
        collection.project_id, collection.name, filter={"_id": document_id}
    )
    if modified:
        audit.log(
            collection,
            actor_id,
            AuditAction.DELETE,
            document_id=document_id,
            before=before,
        )
        webhook.fire(collection, WebhookEvent.DOC_DELETED, {"id": document_id, "before": before})
    return bool(modified)


def restore(
    collection: Collection,
    *,
    document_id: str,
    actor_id: int | None = None,
) -> bool:
    modified = mongo.restore(
        collection.project_id, collection.name, filter={"_id": document_id}
    )
    if modified:
        audit.log(
            collection,
            actor_id,
            AuditAction.RESTORE,
            document_id=document_id,
        )
    return bool(modified)
