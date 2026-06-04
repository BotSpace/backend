"""System (users/chat) collection schemas for cmsv2.

The engine writes bot users into the Mongo `users` collection
({chat_id, first_name, last_name, username, last_seen, created_at}) and the
chat relay writes into `chat`. Documents are only VISIBLE in the dashboard /
MCP when a matching cmsv2 Collection schema exists — this module creates those
schemas (system=True, undeletable from the UI).

Idempotent: safe to call on every project create and from data migrations.
"""

from __future__ import annotations

from core.apps.cms.enums import FieldKind

# (name, label, kind, required)
USERS_FIELDS = [
    ("chat_id", "Chat ID", FieldKind.INT, True),
    ("first_name", "Ism", FieldKind.TEXT, False),
    ("last_name", "Familiya", FieldKind.TEXT, False),
    ("username", "Username", FieldKind.TEXT, False),
    ("last_seen", "Oxirgi faollik", FieldKind.DATETIME, False),
    ("created_at", "Yaratilgan vaqt", FieldKind.DATETIME, False),
]

CHAT_FIELDS = [
    ("chat_id", "Chat ID", FieldKind.TEXT, True),
    ("message", "Xabar", FieldKind.TEXT, False),
    ("message_type", "Xabar turi", FieldKind.TEXT, False),
    ("is_read", "O'qilgan", FieldKind.BOOL, False),
    ("from_admin", "Admindan", FieldKind.BOOL, False),
    ("updated_at", "Yangilangan vaqt", FieldKind.DATETIME, False),
    ("created_at", "Yaratilgan vaqt", FieldKind.DATETIME, False),
]

SYSTEM_COLLECTIONS = {
    "users": {
        "label": "Foydalanuvchilar",
        "description": "Bot foydalanuvchilari (engine avtomatik yozadi).",
        "primary_field": "first_name",
        "fields": USERS_FIELDS,
    },
    "chat": {
        "label": "Chat tarixi",
        "description": "Bot chat xabarlari tarixi.",
        "primary_field": "chat_id",
        "fields": CHAT_FIELDS,
    },
}


def ensure_system_collections(project, *, collection_model=None, field_model=None):
    """Get-or-create the cmsv2 `users`/`chat` system collections for a project.

    `collection_model`/`field_model` are injectable so the data migration can
    pass historical models; defaults to the real models.
    """
    if collection_model is None or field_model is None:
        from core.apps.cms.models.collection import Collection
        from core.apps.cms.models.field import Field

        collection_model = collection_model or Collection
        field_model = field_model or Field

    owner_id = getattr(project, "user_id", None) or getattr(project, "owner_id", None)

    created_any = False
    for name, spec in SYSTEM_COLLECTIONS.items():
        coll = collection_model.objects.filter(
            project_id=project.pk, name=name, deleted_at__isnull=True
        ).first()
        if coll is None:
            coll = collection_model.objects.create(
                project_id=project.pk,
                owner_id=owner_id,
                name=name,
                label=spec["label"],
                description=spec["description"],
                primary_field=spec["primary_field"],
                system=True,
            )
            created_any = True
        elif not coll.system:
            coll.system = True
            coll.save(update_fields=["system"])

        existing = set(coll.fields.values_list("name", flat=True))
        new_fields = [
            field_model(
                collection=coll,
                name=fname,
                label=flabel,
                kind=fkind,
                required=frequired,
                order=i,
            )
            for i, (fname, flabel, fkind, frequired) in enumerate(spec["fields"])
            if fname not in existing
        ]
        if new_fields:
            field_model.objects.bulk_create(new_fields, ignore_conflicts=True)
            created_any = True

    return created_any
