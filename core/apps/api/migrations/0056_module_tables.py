from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0055_enviromentmodel_secret"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModuleModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("icon", models.CharField(blank=True, max_length=255, null=True)),
                ("github_url", models.CharField(blank=True, max_length=500, null=True)),
                ("image", models.CharField(max_length=500)),
                ("port", models.IntegerField(default=8100)),
                ("auth_token", models.CharField(blank=True, max_length=500, null=True)),
                ("manifest_cache", models.JSONField(blank=True, null=True)),
                ("manifest_fetched_at", models.DateTimeField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "ModuleModel",
                "verbose_name_plural": "ModuleModels",
                "db_table": "module",
            },
        ),
        migrations.CreateModel(
            name="ProjectModuleModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("enabled", models.BooleanField(default=True)),
                ("config", models.JSONField(default=dict)),
                ("service_id", models.CharField(blank=True, max_length=255, null=True)),
                ("endpoint", models.CharField(blank=True, max_length=500, null=True)),
                ("status", models.CharField(default="pending", max_length=50)),
                (
                    "module",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_modules",
                        to="api.modulemodel",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_modules",
                        to="api.projectmodel",
                    ),
                ),
            ],
            options={
                "verbose_name": "ProjectModuleModel",
                "verbose_name_plural": "ProjectModuleModels",
                "db_table": "project_module",
                "unique_together": {("project", "module")},
            },
        ),
    ]
