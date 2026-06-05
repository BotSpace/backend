import decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0054_projectmodel_uuid_unique"),
        ("payment", "0007_idempotency_keys"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentOrderModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_orders",
                        to="api.projectmodel",
                        verbose_name="project",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_orders",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                ("payer_chat_id", models.BigIntegerField(verbose_name="payer chat id")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=20, verbose_name="amount")),
                (
                    "commission",
                    models.DecimalField(
                        decimal_places=2, default=decimal.Decimal("0"), max_digits=20, verbose_name="commission"
                    ),
                ),
                (
                    "net_amount",
                    models.DecimalField(
                        decimal_places=2, default=decimal.Decimal("0"), max_digits=20, verbose_name="net amount"
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[("click", "Click"), ("payme", "Payme"), ("paynet", "Paynet"), ("uzum", "Uzum")],
                        default="click",
                        max_length=32,
                        verbose_name="provider",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Yaratildi"),
                            ("paid", "To'landi"),
                            ("cancelled", "Bekor qilindi"),
                            ("refunded", "Qaytarildi"),
                        ],
                        db_index=True,
                        default="created",
                        max_length=32,
                        verbose_name="status",
                    ),
                ),
                ("external_id", models.CharField(blank=True, max_length=128, null=True, verbose_name="external id")),
                ("comment", models.CharField(blank=True, max_length=512, null=True, verbose_name="comment")),
                (
                    "idempotency_key",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        null=True,
                        unique=True,
                        verbose_name="idempotency key",
                    ),
                ),
                ("paid_at", models.DateTimeField(blank=True, null=True, verbose_name="paid at")),
            ],
            options={
                "verbose_name": "Payment Order",
                "verbose_name_plural": "Payment Orders",
                "db_table": "payment_order",
                "ordering": ["-id"],
            },
        ),
    ]
