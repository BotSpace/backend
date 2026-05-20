from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0044_alter_messagemodel_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectmodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
