from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0012_paymentorder_payer_identity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historymodel",
            name="type",
            field=models.CharField(
                choices=[("income", "Kirim"), ("expense", "Chiqim")],
                default="income",
            ),
        ),
    ]
