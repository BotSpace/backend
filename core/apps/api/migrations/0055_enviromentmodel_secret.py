# Generated manually 2026-06-18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0054_projectmodel_uuid_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="enviromentmodel",
            name="secret",
            field=models.BooleanField(default=False, verbose_name="secret"),
        ),
    ]
