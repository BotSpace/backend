from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from django.contrib.auth import get_user_model
from model_bakery import baker

from core.apps.template.enums.withdrawal import WithdrawalStatusEnum

User = get_user_model()


class TemplateWithdrawalRequestModel(AbstractBaseModel):
    """Model for template authors to request withdrawal of their template earnings"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="template_withdrawals",
        verbose_name=_("user")
    )
    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=20,
        decimal_places=2
    )
    card_number = models.CharField(
        verbose_name=_("card number"),
        max_length=20
    )
    card_owner = models.CharField(
        verbose_name=_("card owner"),
        max_length=255
    )
    status = models.CharField(
        max_length=255,
        choices=WithdrawalStatusEnum.choices,
        default=WithdrawalStatusEnum.PENDING.value,
        verbose_name=_("status")
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("rejection reason"),
        help_text=_("Reason for rejection if status is rejected")
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_template_withdrawals",
        verbose_name=_("reviewed by")
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("reviewed at")
    )

    def __str__(self):
        return f"{self.user.phone} - {self.amount} ({self.status})"

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template_withdrawal_request"
        verbose_name = _("Template Withdrawal Request")
        verbose_name_plural = _("Template Withdrawal Requests")
        ordering = ["-created_at"]
