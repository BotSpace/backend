"""Migration: TemplateModel.version + TemplateVersionModel (spec snapshot tarixi)."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("template", "0020_populate_template_spec"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatemodel",
            name="version",
            field=models.PositiveIntegerField(default=1, verbose_name="version"),
        ),
        migrations.CreateModel(
            name="TemplateVersionModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(verbose_name="version")),
                ("spec", models.JSONField(blank=True, default=dict, verbose_name="spec")),
                ("note", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="template_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="template.templatemodel",
                    ),
                ),
            ],
            options={
                "verbose_name": "TemplateVersionModel",
                "verbose_name_plural": "TemplateVersionModels",
                "db_table": "template_version",
                "ordering": ["-version"],
                "unique_together": {("template", "version")},
            },
        ),
    ]
