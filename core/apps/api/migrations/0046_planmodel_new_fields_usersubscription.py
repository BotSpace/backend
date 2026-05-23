import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0045_projectmodel_deleted_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # PlanModel yangi maydonlari
        migrations.AddField(
            model_name="planmodel",
            name="max_bots",
            field=models.IntegerField(default=1, verbose_name="Maksimal botlar soni"),
        ),
        migrations.AddField(
            model_name="planmodel",
            name="max_output_tokens",
            field=models.BigIntegerField(default=200000, verbose_name="Oylik output token limiti"),
        ),
        migrations.AddField(
            model_name="planmodel",
            name="max_input_tokens",
            field=models.BigIntegerField(default=1000000, verbose_name="Oylik input token limiti"),
        ),
        migrations.AddField(
            model_name="planmodel",
            name="features",
            field=models.JSONField(blank=True, default=dict, verbose_name="Xususiyatlar"),
        ),
        # PlanType choices ni yangilash (free/pro/max)
        migrations.AlterField(
            model_name="planmodel",
            name="name",
            field=models.CharField(
                choices=[("free", "Free"), ("pro", "Pro"), ("max", "Max")],
                max_length=50,
                unique=True,
                verbose_name="Nom",
            ),
        ),
        # UserSubscription jadvali
        migrations.CreateModel(
            name="UserSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Faol"),
                            ("suspended", "To'xtatilgan"),
                            ("grace_period", "Imkoniyat muddati"),
                            ("cancelled", "Bekor qilingan"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("tokens_used_input", models.BigIntegerField(default=0)),
                ("tokens_used_output", models.BigIntegerField(default=0)),
                ("token_reset_at", models.DateTimeField(auto_now_add=True)),
                ("bots_count", models.IntegerField(default=0)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_subscriptions",
                        to="api.planmodel",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Foydalanuvchi tarifi",
                "verbose_name_plural": "Foydalanuvchi tariflari",
                "db_table": "user_subscription",
            },
        ),
    ]
