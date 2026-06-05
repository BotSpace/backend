from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("template", "0017_templateordermodel_commission_paid_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatemodel",
            name="required_envs",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of required env vars. Format: [{"key": "ADMIN_CHAT_ID", "description": "..."}]',
                verbose_name="required envs",
            ),
        ),
        migrations.AddField(
            model_name="templatesubmissionrequestmodel",
            name="required_envs",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of required env vars. Format: [{"key": "ADMIN_CHAT_ID", "description": "..."}]',
                verbose_name="required envs",
            ),
        ),
    ]
