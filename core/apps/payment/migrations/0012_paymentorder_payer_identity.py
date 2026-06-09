from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0011_withdrawalrequestmodel"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentordermodel",
            name="payer_first_name",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="payer first name"),
        ),
        migrations.AddField(
            model_name="paymentordermodel",
            name="payer_last_name",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="payer last name"),
        ),
        migrations.AddField(
            model_name="paymentordermodel",
            name="payer_username",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="payer username"),
        ),
    ]
