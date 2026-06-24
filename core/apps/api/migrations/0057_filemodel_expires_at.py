from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0056_module_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="filemodel",
            name="expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
