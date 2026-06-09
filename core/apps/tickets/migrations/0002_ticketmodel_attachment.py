from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticketmodel",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="Ixtiyoriy fayl (rasm yoki hujjat)",
                null=True,
                upload_to="tickets/",
                verbose_name="attachment",
            ),
        ),
    ]
