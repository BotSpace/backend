import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def move_messages_forward(apps, schema_editor):
    """Mavjud murojaatlarning matnini xabarlar oqimiga ko'chiradi."""
    Ticket = apps.get_model("tickets", "TicketModel")
    Message = apps.get_model("tickets", "TicketMessageModel")
    for t in Ticket.objects.all():
        if getattr(t, "message", None):
            Message.objects.create(
                ticket=t,
                sender="user",
                author_id=t.user_id,
                message=t.message,
                attachment=t.attachment or None,
            )
        if getattr(t, "admin_reply", None):
            Message.objects.create(ticket=t, sender="admin", message=t.admin_reply)


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0002_ticketmodel_attachment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketMessageModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sender", models.CharField(choices=[("user", "User"), ("admin", "Admin")], default="user", max_length=16, verbose_name="sender")),
                ("message", models.TextField(verbose_name="message")),
                ("attachment", models.FileField(blank=True, help_text="Ixtiyoriy fayl (rasm yoki hujjat)", null=True, upload_to="tickets/", verbose_name="attachment")),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ticket_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="author",
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="tickets.ticketmodel",
                        verbose_name="ticket",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ticket Message",
                "verbose_name_plural": "Ticket Messages",
                "db_table": "support_ticket_message",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.RunPython(move_messages_forward, migrations.RunPython.noop),
        migrations.RemoveField(model_name="ticketmodel", name="message"),
        migrations.RemoveField(model_name="ticketmodel", name="attachment"),
        migrations.RemoveField(model_name="ticketmodel", name="admin_reply"),
    ]
