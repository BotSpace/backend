from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0005_remove_historymodel_project_historymodel_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historymodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
