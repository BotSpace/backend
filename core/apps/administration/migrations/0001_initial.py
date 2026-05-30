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
            name="AdminAuditLogModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        help_text=(
                            "Dotted code: domain.verb (user.ban, user.balance_set, "
                            "template.verify, withdrawal.approve, withdrawal.reject, "
                            "plan.create, plan.update, plan.delete, ticket.respond, ...)"
                        ),
                        max_length=120,
                    ),
                ),
                ("target_type", models.CharField(blank=True, default="", max_length=60)),
                ("target_id", models.CharField(blank=True, default="", max_length=60)),
                ("payload_before", models.JSONField(blank=True, null=True)),
                ("payload_after", models.JSONField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Actor (admin user)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Admin audit log entry",
                "verbose_name_plural": "Admin audit log",
                "db_table": "admin_audit_log",
                "ordering": ("-id",),
            },
        ),
        migrations.AddIndex(
            model_name="adminauditlogmodel",
            index=models.Index(fields=["actor", "-id"], name="admin_audit_actor_id_idx"),
        ),
        migrations.AddIndex(
            model_name="adminauditlogmodel",
            index=models.Index(fields=["target_type", "target_id"], name="admin_audit_target_idx"),
        ),
        migrations.AddIndex(
            model_name="adminauditlogmodel",
            index=models.Index(fields=["action", "-id"], name="admin_audit_action_idx"),
        ),
    ]
