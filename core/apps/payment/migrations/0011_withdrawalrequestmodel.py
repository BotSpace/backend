import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0010_paymentorder_is_debug"),
        ("api", "0054_projectmodel_uuid_unique"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WithdrawalRequestModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=20, verbose_name="amount")),
                ("card_number", models.CharField(max_length=20, verbose_name="card number")),
                ("card_owner", models.CharField(max_length=255, verbose_name="card owner")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=32, verbose_name="status")),
                ("rejection_reason", models.TextField(blank=True, null=True, verbose_name="rejection reason")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="reviewed at")),
                ("project", models.ForeignKey(blank=True, help_text="Qaysi bot uchun pul yechilmoqda (umumiy balansdan ayriladi)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="withdrawals", to="api.projectmodel", verbose_name="bot")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_bot_withdrawals", to=settings.AUTH_USER_MODEL, verbose_name="reviewed by")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bot_withdrawals", to=settings.AUTH_USER_MODEL, verbose_name="user")),
            ],
            options={
                "verbose_name": "Withdrawal Request",
                "verbose_name_plural": "Withdrawal Requests",
                "db_table": "payment_withdrawal_request",
                "ordering": ["-created_at"],
            },
        ),
    ]
