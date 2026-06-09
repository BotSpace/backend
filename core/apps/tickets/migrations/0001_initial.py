import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("subject", models.CharField(max_length=255, verbose_name="subject")),
                ("message", models.TextField(verbose_name="message")),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("pending", "Pending"), ("closed", "Closed")],
                        db_index=True,
                        default="open",
                        max_length=32,
                        verbose_name="status",
                    ),
                ),
                ("admin_reply", models.TextField(blank=True, help_text="Admin javobi", null=True, verbose_name="admin reply")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ticket",
                "verbose_name_plural": "Tickets",
                "db_table": "support_ticket",
                "ordering": ["-created_at"],
            },
        ),
    ]
