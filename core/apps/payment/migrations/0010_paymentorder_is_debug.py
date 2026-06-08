from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0009_paymentorder_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentordermodel",
            name="is_debug",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True if the order was created by the debug engine. Determines which "
                    "engine service (debug vs release webhook uuid) receives the payment callback."
                ),
                verbose_name="is debug",
            ),
        ),
    ]
