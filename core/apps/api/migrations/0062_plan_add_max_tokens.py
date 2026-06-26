from django.db import migrations, models


def populate_max_tokens(apps, schema_editor):
    """max_tokens = max_input_tokens + max_output_tokens (mavjud qatorlar uchun)."""
    PlanModel = apps.get_model("api", "PlanModel")
    for plan in PlanModel.objects.all():
        plan.max_tokens = plan.max_input_tokens + plan.max_output_tokens
        plan.save(update_fields=["max_tokens"])


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0061_projectresourcesnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="planmodel",
            name="max_tokens",
            field=models.BigIntegerField(default=1000000, verbose_name="Oylik token limiti"),
        ),
        migrations.RunPython(populate_max_tokens, reverse_code=reverse_populate),
    ]
