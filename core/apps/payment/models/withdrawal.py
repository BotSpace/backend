from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.payment.enums.withdrawal import WithdrawalStatusEnum

User = get_user_model()


class WithdrawalRequestModel(AbstractBaseModel):
    """Bot daromadlaridan pul yechish so'rovi.

    Daromad bitta umumiy balansda (``User.balance``) yig'iladi. ``project``
    qaysi bot uchun yechilayotganini bildiradi (hisobot/filtr uchun), summa
    esa umumiy balansdan ayriladi. Balans faqat admin tasdiqlaganda yechiladi.
    Pul yechish uchun foydalanuvchi avval KYC verifikatsiyadan o'tgan
    bo'lishi shart.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bot_withdrawals",
        verbose_name=_("user"),
    )
    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawals",
        verbose_name=_("bot"),
        help_text=_("Qaysi bot uchun pul yechilmoqda (umumiy balansdan ayriladi)"),
    )
    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=20,
        decimal_places=2,
    )
    card_number = models.CharField(
        verbose_name=_("card number"),
        max_length=20,
    )
    card_owner = models.CharField(
        verbose_name=_("card owner"),
        max_length=255,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=32,
        choices=WithdrawalStatusEnum.choices,
        default=WithdrawalStatusEnum.PENDING.value,
    )
    rejection_reason = models.TextField(
        verbose_name=_("rejection reason"),
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_bot_withdrawals",
        verbose_name=_("reviewed by"),
    )
    reviewed_at = models.DateTimeField(
        verbose_name=_("reviewed at"),
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user.phone} - {self.amount} ({self.status})"

    class Meta:
        db_table = "payment_withdrawal_request"
        verbose_name = _("Withdrawal Request")
        verbose_name_plural = _("Withdrawal Requests")
        ordering = ["-created_at"]
