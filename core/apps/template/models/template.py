from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.contrib.postgres.indexes import GinIndex

from core.apps.template.enums.template import DiscountTypeEnum
from core.utils.encoder import PrettyJSONEncoder
from django.contrib.postgres.search import SearchVector


User = get_user_model()


class TemplateModel(AbstractBaseModel):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name=_("name"), max_length=255)
    image = models.ImageField(_("image"), upload_to="template/")
    video = models.FileField(upload_to="template-video/", null=True, blank=True)
    short_description = models.TextField(_("short description"))
    description = models.TextField(_("description"))
    flow = models.JSONField(verbose_name=_("flow"), default=list, null=True, blank=True, encoder=PrettyJSONEncoder)
    original_price = models.DecimalField(max_digits=20, decimal_places=2)
    discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    features = models.ManyToManyField("TemplateFeatureModel", null=True, blank=True)
    categories = models.ManyToManyField("TemplateCategoryModel", null=True, blank=True)
    views = models.BigIntegerField(default=0)
    discount_type = models.CharField(
        max_length=255,
        choices=DiscountTypeEnum.choices,
        default=DiscountTypeEnum.PERCENT.value,
    )

    def __str__(self):
        return "%s - %s" % (self.name, self.author.first_name)

    @property
    def price(self):
        if self.discount == Decimal("0.00"):
            return self.original_price
        if self.discount_type == DiscountTypeEnum.AMOUNT.value:
            return self.original_price - self.discount
        return self.original_price - (self.original_price / Decimal("100") * self.discount)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template"
        verbose_name = _("TemplateModel")
        verbose_name_plural = _("TemplateModels")


class TemplateLikeModel(AbstractBaseModel):
    template = models.ForeignKey("TemplateModel", on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=False)

    def __str__(self) -> str:
        return self.template.name

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template_like"
        verbose_name = _("TemplateLikeModel")
        verbose_name_plural = _("TemplateLikeModels")


class TemplateFeatureModel(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    value = models.TextField(_("value"), null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template_feature"
        verbose_name = _("TemplateFeatureModel")
        verbose_name_plural = _("TemplateFeatureModels")


class TemplateCategoryModel(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template_category"
        verbose_name = _("TemplateCategoryModel")
        verbose_name_plural = _("TemplateCategoryModels")


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
