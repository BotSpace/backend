from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0013_alter_historymodel_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentordermodel",
            name="pay_instruction",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Paycue HTML payment instruction stored at create time; empty for non-paycue orders.",
                verbose_name="pay instruction",
            ),
        ),
    ]
