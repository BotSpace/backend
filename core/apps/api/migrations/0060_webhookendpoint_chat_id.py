from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0059_webhook_endpoint"),
    ]

    operations = [
        migrations.AddField(
            model_name="webhookendpointmodel",
            name="chat_id",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterUniqueTogether(
            name="webhookendpointmodel",
            unique_together={("project", "node_id", "chat_id")},
        ),
    ]
