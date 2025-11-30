from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker

from core.apps.api.models.project import ProjectModel


class HistoryModel(AbstractBaseModel):
    TYPES = (
        ("cpu", "cpu"),
        ("ram", "ram"),
        ("net_rx", "net_rx"),
        ("net_tx", "net_tx"),
        ("storage", "storage"),
    )
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    comment = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(choices=TYPES, default="cpu")
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "history"
        verbose_name = _("HistoryModel")
        verbose_name_plural = _("HistoryModels")
