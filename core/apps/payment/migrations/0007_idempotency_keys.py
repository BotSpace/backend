from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0006_softdelete_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="historymodel",
            name="idempotency_key",
            field=models.CharField(
                blank=True,
                help_text=(
                    "External idempotency key — duplicate requests "
                    "with the same key are ignored."
                ),
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="idempotency_key",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Client-supplied idempotency key — duplicate POSTs "
                    "with the same key return the original transaction."
                ),
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
    ]
