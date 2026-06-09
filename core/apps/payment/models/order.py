from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_bakery import baker

from core.apps.shared.models import SoftDeleteModel
from core.apps.payment.enums.payment import PaymentMethosEnum, PaymentOrderStatusEnum

User = get_user_model()


class PaymentOrderModel(SoftDeleteModel):
    """Bot foydalanuvchisidan to'lov qabul qilish uchun order.

    Oqim: engine → order/create/ → Click pay_url → mijoz to'laydi →
    webhook → egaga net kredit + Botspace komissiya → engine xabardor qilinadi.
    """

    project = models.ForeignKey(
        "api.ProjectModel",
        verbose_name=_("project"),
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )
    owner = models.ForeignKey(
        User,
        verbose_name=_("owner"),
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )
    payer_chat_id = models.BigIntegerField(
        verbose_name=_("payer chat id"),
        help_text=_("Telegram chat_id of the bot user who is paying"),
    )
    payer_first_name = models.CharField(
        verbose_name=_("payer first name"),
        max_length=255,
        null=True,
        blank=True,
    )
    payer_last_name = models.CharField(
        verbose_name=_("payer last name"),
        max_length=255,
        null=True,
        blank=True,
    )
    payer_username = models.CharField(
        verbose_name=_("payer username"),
        max_length=255,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=20,
        decimal_places=2,
        help_text=_("Full amount the user pays (so'm)"),
    )
    commission = models.DecimalField(
        verbose_name=_("commission"),
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Botspace commission (amount * rate)"),
    )
    net_amount = models.DecimalField(
        verbose_name=_("net amount"),
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Amount credited to owner (amount - commission)"),
    )
    provider = models.CharField(
        verbose_name=_("provider"),
        max_length=32,
        choices=PaymentMethosEnum.choices,
        default=PaymentMethosEnum.CLICK,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=32,
        choices=PaymentOrderStatusEnum.choices,
        default=PaymentOrderStatusEnum.CREATED,
        db_index=True,
    )
    external_id = models.CharField(
        verbose_name=_("external id"),
        max_length=128,
        null=True,
        blank=True,
        help_text=_("Click/Payme transaction id from the provider"),
    )
    comment = models.CharField(
        verbose_name=_("comment"),
        max_length=512,
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(
        verbose_name=_("idempotency key"),
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        help_text=_("Client-supplied idempotency key; duplicate order-create requests with same key return the existing order."),
    )
    transaction = models.OneToOneField(
        "payment.TransactionModel",
        verbose_name=_("transaction"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_order",
    )
    paid_at = models.DateTimeField(
        verbose_name=_("paid at"),
        null=True,
        blank=True,
    )
    is_debug = models.BooleanField(
        verbose_name=_("is debug"),
        default=False,
        help_text=_(
            "True if the order was created by the debug engine. Determines which "
            "engine service (debug vs release webhook uuid) receives the payment callback."
        ),
    )

    def __str__(self):
        return f"PaymentOrder #{self.pk} | {self.project_id} | {self.status}"

    @classmethod
    def _baker(cls):
        from core.apps.api.models.project import ProjectModel

        owner = User._create_fake()
        project = baker.make(ProjectModel, owner=owner)
        return baker.make(
            cls,
            project=project,
            owner=owner,
            amount=Decimal("10000"),
            deleted_at=None,
        )

    class Meta:
        db_table = "payment_order"
        verbose_name = _("Payment Order")
        verbose_name_plural = _("Payment Orders")
        ordering = ["-id"]
