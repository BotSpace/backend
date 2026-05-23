from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_alter_user_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="PersonalAccessToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Nomi")),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True, verbose_name="Token hash")),
                ("prefix", models.CharField(max_length=12, verbose_name="Prefix")),
                ("last_used_at", models.DateTimeField(blank=True, null=True, verbose_name="Oxirgi ishlatilgan")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_tokens", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "API token",
                "verbose_name_plural": "API tokenlar",
                "db_table": "personal_access_token",
                "ordering": ["-created_at"],
            },
        ),
    ]
