from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("api", "0049_remove_project_plan_model_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CredentialType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=80, unique=True, verbose_name="key")),
                ("label", models.CharField(max_length=120, verbose_name="label")),
                ("description", models.TextField(blank=True, default="", verbose_name="description")),
                ("icon", models.CharField(blank=True, default="", max_length=64, verbose_name="icon")),
                (
                    "mode",
                    models.CharField(
                        choices=[
                            ("apikey", "API Key"),
                            ("bearer", "Bearer Token"),
                            ("header", "Header Auth"),
                            ("basic", "Basic Auth"),
                            ("none", "None"),
                        ],
                        max_length=16,
                        verbose_name="mode",
                    ),
                ),
                ("fields", models.JSONField(blank=True, default=list, verbose_name="fields")),
                ("system", models.BooleanField(default=False, verbose_name="system")),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="credential_types",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "credential_type",
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="Credential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="name")),
                ("data_encrypted", models.TextField(verbose_name="data encrypted")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="deleted at")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credentials",
                        to="api.projectmodel",
                        verbose_name="project",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_credentials",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                (
                    "type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="credentials",
                        to="credentials.credentialtype",
                        verbose_name="type",
                    ),
                ),
            ],
            options={
                "db_table": "credential",
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="credential",
            index=models.Index(fields=["project", "deleted_at"], name="credential_project_deleted_idx"),
        ),
        migrations.AddConstraint(
            model_name="credential",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("project", "name"),
                name="credential_unique_name_per_project",
            ),
        ),
    ]
