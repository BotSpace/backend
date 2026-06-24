import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0058_modulemodel_is_default"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookEndpointModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("node_id", models.CharField(max_length=255)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_endpoints",
                        to="api.projectmodel",
                    ),
                ),
            ],
            options={
                "verbose_name": "WebhookEndpoint",
                "verbose_name_plural": "WebhookEndpoints",
                "db_table": "webhook_endpoint",
                "unique_together": {("project", "node_id")},
            },
        ),
    ]
