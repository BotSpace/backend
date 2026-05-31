"""Step 2/3: Populate uuid for all existing ProjectModel rows."""

from __future__ import annotations

import uuid

from django.db import migrations


def _populate_uuid(apps, schema_editor):
    ProjectModel = apps.get_model("api", "ProjectModel")
    rows = ProjectModel.objects.filter(uuid__isnull=True).only("pk")
    for row in rows.iterator(chunk_size=500):
        ProjectModel.objects.filter(pk=row.pk).update(uuid=uuid.uuid4())


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0052_projectmodel_uuid_add"),
    ]

    operations = [
        migrations.RunPython(_populate_uuid, reverse_code=_noop),
    ]
