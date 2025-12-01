from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker
from django.contrib.auth import get_user_model


User = get_user_model()


class TransactionModel(AbstractBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "transaction"
        verbose_name = _("TransactionModel")
        verbose_name_plural = _("TransactionModels")
