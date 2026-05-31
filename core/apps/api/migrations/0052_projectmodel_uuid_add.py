"""Step 1/3: Add uuid column to project table (nullable, no unique constraint yet)."""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0051_drop_orphaned_project_plan_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectmodel",
            name="uuid",
            field=models.UUIDField(blank=True, db_index=True, default=uuid.uuid4, editable=False, null=True),
        ),
    ]
