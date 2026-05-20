from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_bakery import baker

from core.apps.shared.models import SoftDeleteModel


User = get_user_model()


class HistoryModel(SoftDeleteModel):
    TYPES = (
        ("income", "income"),
        ("expense", "expense"),
    )
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    comment = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(choices=TYPES, default="cpu")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=False)
    idempotency_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        help_text=_("External idempotency key — duplicate requests with the same key are ignored."),
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls, _fill_optional=True)

    class Meta:
        db_table = "history"
        verbose_name = _("HistoryModel")
        verbose_name_plural = _("HistoryModels")
