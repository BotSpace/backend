from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.accounts.choices.verification import VerificationStatusChoice
from core.apps.shared.validators import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    image_extension_validator,
    validate_document_size,
    validate_image_size,
)

User = get_user_model()

# Ma'lumotnoma (yashash joyidan) rasm yoki PDF/hujjat ko'rinishida bo'lishi mumkin.
reference_extension_validator = FileExtensionValidator(IMAGE_EXTENSIONS + DOCUMENT_EXTENSIONS)


class UserVerificationModel(AbstractBaseModel):
    """Foydalanuvchining KYC verifikatsiya so'rovi.

    Pul yechishdan oldin foydalanuvchi pasport, o'z rasmi (selfie) va yashash
    joyidan ma'lumotnoma yuboradi. Admin tasdiqlasa `User.kyc_verified_at`
    o'rnatiladi va keyingi barcha pul yechishlar ochiladi.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verifications",
        verbose_name=_("user"),
    )
    full_name = models.CharField(
        verbose_name=_("full name"),
        max_length=255,
        help_text=_("Pasportdagi to'liq ism-sharif"),
    )
    passport_image = models.FileField(
        verbose_name=_("passport image"),
        upload_to="kyc/passport/",
        validators=[image_extension_validator, validate_image_size],
    )
    selfie_image = models.FileField(
        verbose_name=_("selfie image"),
        upload_to="kyc/selfie/",
        validators=[image_extension_validator, validate_image_size],
        help_text=_("Pasport bilan birga olingan shaxsiy rasm"),
    )
    residence_reference = models.FileField(
        verbose_name=_("residence reference"),
        upload_to="kyc/residence/",
        validators=[reference_extension_validator, validate_document_size],
        help_text=_("Yashash joyidan ma'lumotnoma (rasm yoki PDF)"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=32,
        choices=VerificationStatusChoice.choices,
        default=VerificationStatusChoice.PENDING.value,
    )
    rejection_reason = models.TextField(
        verbose_name=_("rejection reason"),
        null=True,
        blank=True,
        help_text=_("Rad etilgan bo'lsa sababi"),
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_verifications",
        verbose_name=_("reviewed by"),
    )
    reviewed_at = models.DateTimeField(
        verbose_name=_("reviewed at"),
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user.phone} - {self.status}"

    class Meta:
        db_table = "user_verification"
        verbose_name = _("User Verification")
        verbose_name_plural = _("User Verifications")
        ordering = ["-created_at"]
