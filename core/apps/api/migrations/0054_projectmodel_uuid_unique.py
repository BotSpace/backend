"""Step 3/3: Make uuid unique=True, null=False."""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0053_projectmodel_uuid_populate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="projectmodel",
            name="uuid",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
