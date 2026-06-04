"""Backfill cmsv2 system collections (users/chat) for all existing projects.

Pure DML (INSERTs) — no DDL, safe with prod table ownership. The engine
(3.5.29-prod+) writes bot users into the Mongo `users` collection; these
schema rows make that data visible in the dashboard CMS and MCP.
"""

from django.db import migrations

# Kept in sync with core.apps.cms.services.system_collections (copied here so
# the migration stays stable if the service evolves).
SYSTEM_COLLECTIONS = {
    "users": {
        "label": "Foydalanuvchilar",
        "description": "Bot foydalanuvchilari (engine avtomatik yozadi).",
        "primary_field": "first_name",
        "fields": [
            ("chat_id", "Chat ID", "int", True),
            ("first_name", "Ism", "text", False),
            ("last_name", "Familiya", "text", False),
            ("username", "Username", "text", False),
            ("last_seen", "Oxirgi faollik", "datetime", False),
            ("created_at", "Yaratilgan vaqt", "datetime", False),
        ],
    },
    "chat": {
        "label": "Chat tarixi",
        "description": "Bot chat xabarlari tarixi.",
        "primary_field": "chat_id",
        "fields": [
            ("chat_id", "Chat ID", "text", True),
            ("message", "Xabar", "text", False),
            ("message_type", "Xabar turi", "text", False),
            ("is_read", "O'qilgan", "bool", False),
            ("from_admin", "Admindan", "bool", False),
            ("updated_at", "Yangilangan vaqt", "datetime", False),
            ("created_at", "Yaratilgan vaqt", "datetime", False),
        ],
    },
}


def backfill(apps, schema_editor):
    Project = apps.get_model("api", "ProjectModel")
    Collection = apps.get_model("cms", "Collection")
    Field = apps.get_model("cms", "Field")

    projects = Project.objects.filter(deleted_at__isnull=True).only("id", "user")
    for project in projects.iterator(chunk_size=500):
        for name, spec in SYSTEM_COLLECTIONS.items():
            coll = Collection.objects.filter(
                project_id=project.id, name=name, deleted_at__isnull=True
            ).first()
            if coll is None:
                coll = Collection.objects.create(
                    project_id=project.id,
                    owner_id=project.user_id,
                    name=name,
                    label=spec["label"],
                    description=spec["description"],
                    primary_field=spec["primary_field"],
                    system=True,
                )
            elif not coll.system:
                coll.system = True
                coll.save(update_fields=["system"])

            existing = set(Field.objects.filter(collection=coll).values_list("name", flat=True))
            new_fields = [
                Field(
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
                Field.objects.bulk_create(new_fields, ignore_conflicts=True)


def noop(apps, schema_editor):
    """System collections are kept on reverse — deleting user data is worse."""


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0002_collection_primary_field"),
        ("api", "0054_projectmodel_uuid_unique"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
