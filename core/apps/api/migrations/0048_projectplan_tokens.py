from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0047_seed_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectplanmodel",
            name="tokens_used_input",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="projectplanmodel",
            name="tokens_used_output",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="projectplanmodel",
            name="token_reset_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="projectplanmodel",
            name="token_reset_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
