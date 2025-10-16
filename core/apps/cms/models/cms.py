# type: ignore
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.apps.cms.enums import FieldType
from django_core.models import AbstractBaseModel
from model_bakery import baker

User = get_user_model()


class CollectionModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey("api.ProjectModel", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return baker(cls, user=User._create_fake())

    class Meta:
        db_table = "collection"
        verbose_name = _("CollectionModel")
        verbose_name_plural = _("CollectionModels")
        constraints = [models.UniqueConstraint(fields=["name", "project"], name="name_project_collection")]


class FieldModel(AbstractBaseModel):
    collection = models.ForeignKey("CollectionModel", on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(verbose_name=_("name"), max_length=255)
    type = models.CharField(_("name"), max_length=255, default=FieldType.TEXT.value, choices=FieldType.choices)
    required = models.BooleanField(_("required"), default=False)
    default = models.CharField(_("default"), max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return baker(cls)

    class Meta:
        db_table = "field"
        verbose_name = _("FieldModel")
        verbose_name_plural = _("FieldModels")
        constraints = [models.UniqueConstraint(fields=["name", "collection"], name="field_name_collection_constraint")]
