from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_bakery import baker

from core.apps.shared.models import SoftDeleteModel


User = get_user_model()


class TransactionModel(SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.BooleanField(default=False)
    idempotency_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        help_text=_("Client-supplied idempotency key — duplicate POSTs with the same key return the original transaction."),
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "transaction"
        verbose_name = _("TransactionModel")
        verbose_name_plural = _("TransactionModels")
