"""Backfill data migration: mavjud barcha loyihalar uchun 'users' va 'chat'
kolleksiyalarini yaratadi (agar yo'q bo'lsa).

Bu sof DML migratsiya — CREATE TABLE/ALTER TABLE operatsiyalari yo'q,
shuning uchun PostgreSQL ownership muammosi kelib chiqmaydi.
"""

from django.db import migrations


def _create_default_collections(apps, schema_editor):
    ProjectModel = apps.get_model("api", "ProjectModel")
    CollectionModel = apps.get_model("cms_legacy", "CollectionModel")
    FieldModel = apps.get_model("cms_legacy", "FieldModel")

    USERS_FIELDS = [
        # (name, type, required)
        ("chat_id", "number", True),
        ("first_name", "text", False),
        ("last_name", "text", False),
        ("username", "text", False),
        ("last_seen", "datetime", False),
        ("created_at", "datetime", False),
    ]

    CHAT_FIELDS = [
        ("chat_id", "text", True),
        ("message", "text", False),
        ("message_type", "text", False),
        ("is_read", "bool", False),
        ("from_admin", "bool", False),
        ("updated_at", "datetime", False),
        ("created_at", "datetime", False),
    ]

    DEFAULT_COLLECTIONS = {
        "users": USERS_FIELDS,
        "chat": CHAT_FIELDS,
    }

    for project in ProjectModel.objects.filter(deleted_at__isnull=True).select_related("owner"):
        for collection_name, field_defs in DEFAULT_COLLECTIONS.items():
            collection, created = CollectionModel.objects.get_or_create(
                name=collection_name,
                project=project,
                defaults={"user": project.owner},
            )

            if not created:
                continue

            fields = [
                FieldModel(
                    collection=collection,
                    name=field_name,
                    type=field_type,
                    required=required,
                )
                for field_name, field_type, required in field_defs
            ]
            FieldModel.objects.bulk_create(fields, ignore_conflicts=True)


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cms_legacy", "0010_alter_collectionmodel_project"),
        ("api", "0054_projectmodel_uuid_unique"),
    ]

    operations = [
        migrations.RunPython(_create_default_collections, reverse_code=_noop),
    ]
