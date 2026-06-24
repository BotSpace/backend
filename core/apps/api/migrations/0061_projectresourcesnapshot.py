import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0060_webhookendpoint_chat_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectResourceSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("disk_bytes", models.BigIntegerField(default=0)),
                ("disk_files_bytes", models.BigIntegerField(default=0)),
                ("disk_cms_bytes", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resource_snapshots",
                        to="api.projectmodel",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectresourcesnapshot",
            index=models.Index(fields=["project", "created_at"], name="api_project_project_e3c5d1_idx"),
        ),
    ]
