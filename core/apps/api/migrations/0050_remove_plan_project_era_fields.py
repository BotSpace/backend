"""Drop project-era PlanModel fields.

Plans are now attached to USERS (UserSubscription), not projects. These
four fields were never enforced anywhere in the codebase and described
project-level concepts (max end-users per bot, per-bot branding, custom
domain, support tier). Removed along with the leftover seed/admin/
serializer references.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0049_remove_project_plan_model_state"),
    ]

    operations = [
        migrations.RemoveField(model_name="planmodel", name="max_users"),
        migrations.RemoveField(model_name="planmodel", name="powered_by_botmother"),
        migrations.RemoveField(model_name="planmodel", name="custom_domain"),
        migrations.RemoveField(model_name="planmodel", name="priority_support"),
        migrations.AlterField(
            model_name="planmodel",
            name="max_bots",
            field=models.IntegerField(default=1, help_text="0 = cheksiz", verbose_name="Maksimal botlar soni"),
        ),
        migrations.AlterField(
            model_name="planmodel",
            name="max_input_tokens",
            field=models.BigIntegerField(default=800000, verbose_name="Oylik input token limiti"),
        ),
    ]
