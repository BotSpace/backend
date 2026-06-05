import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0008_add_payment_order_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentordermodel",
            name="transaction",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payment_order",
                to="payment.transactionmodel",
                verbose_name="transaction",
            ),
        ),
    ]
