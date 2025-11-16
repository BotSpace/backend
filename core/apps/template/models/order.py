from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker

from core.apps.template.enums.order import TemplateOrderStatusEnum

User = get_user_model()


class TemplateOrderModel(AbstractBaseModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=False)
    template = models.ForeignKey("TemplateModel", on_delete=models.SET_NULL, null=True, blank=False)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.CharField(
        _("status"), choices=TemplateOrderStatusEnum.choices, default=TemplateOrderStatusEnum.PENDING.value
    )
    payment_status = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % self.user.first_name

    @classmethod
    def _baker(cls):
        return baker.make(cls, _fill_optional=True)

    class Meta:
        db_table = "templae_order"
        verbose_name = _("TemplaeOrderModel")
        verbose_name_plural = _("TemplateOrderModels")
