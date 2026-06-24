from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0057_filemodel_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="modulemodel",
            name="is_default",
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
