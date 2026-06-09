import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_remove_user_prompt_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="kyc_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="UserVerificationModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(help_text="Pasportdagi to'liq ism-sharif", max_length=255, verbose_name="full name")),
                ("passport_image", models.FileField(upload_to="kyc/passport/", verbose_name="passport image")),
                ("selfie_image", models.FileField(help_text="Pasport bilan birga olingan shaxsiy rasm", upload_to="kyc/selfie/", verbose_name="selfie image")),
                ("residence_reference", models.FileField(help_text="Yashash joyidan ma'lumotnoma (rasm yoki PDF)", upload_to="kyc/residence/", verbose_name="residence reference")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=32, verbose_name="status")),
                ("rejection_reason", models.TextField(blank=True, help_text="Rad etilgan bo'lsa sababi", null=True, verbose_name="rejection reason")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="reviewed at")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_verifications", to=settings.AUTH_USER_MODEL, verbose_name="reviewed by")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="verifications", to=settings.AUTH_USER_MODEL, verbose_name="user")),
            ],
            options={
                "verbose_name": "User Verification",
                "verbose_name_plural": "User Verifications",
                "db_table": "user_verification",
                "ordering": ["-created_at"],
            },
        ),
    ]
