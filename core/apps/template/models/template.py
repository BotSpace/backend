from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker
from django.contrib.auth import get_user_model

from core.apps.template.enums.template import TemplateTypeEnum


User = get_user_model()


class TemplateModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    flow = models.JSONField(verbose_name=_("flow"))
    price = models.DecimalField(max_digits=20, decimal_places=2)
    discount = models.DecimalField(max_digits=20, decimal_places=2)
    discount_type = models.CharField(
        max_length=255,
        choices=TemplateTypeEnum.choices,
        default=TemplateTypeEnum.PERCENT.value,
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template"
        verbose_name = _("TemplateModel")
        verbose_name_plural = _("TemplateModels")


class UserTemplateModel(AbstractBaseModel):
    user = models.ForeignKey(to=User, verbose_name=_("user"), on_delete=models.CASCADE)
    template = models.ForeignKey("TemplateModel", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "usertemplate"
        verbose_name = _("UsertemplateModel")
        verbose_name_plural = _("UsertemplateModels")
