from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shared", "0002_settingsmodel_created_at_settingsmodel_description_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Config",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(db_index=True, max_length=255, unique=True, verbose_name="key")),
                ("value", models.JSONField(blank=True, default=None, null=True, verbose_name="value")),
                ("label", models.CharField(blank=True, max_length=255, verbose_name="label")),
                ("group", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="group")),
                ("is_public", models.BooleanField(default=True, verbose_name="is public")),
                ("description", models.TextField(blank=True, verbose_name="description")),
            ],
            options={
                "verbose_name": "Config",
                "verbose_name_plural": "Configs",
                "db_table": "global_config",
                "ordering": ["group", "key"],
            },
        ),
    ]
