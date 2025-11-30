from django.db import models
from django_core.models import AbstractBaseModel
import uuid
from django.contrib.auth import get_user_model
from model_bakery import baker

from core.apps.api.models.project import ProjectModel
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class ResourceModel(AbstractBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE)
    hostname = models.CharField()

    ram = models.IntegerField()
    cpu = models.IntegerField()
    net_rx = models.BigIntegerField()
    net_tx = models.BigIntegerField()

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "resource"
        verbose_name = _("ResourceModel")
        verbose_name_plural = _("ResourceModels")


class StorageResourceModel(AbstractBaseModel):
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE)
    storage = models.BigIntegerField(default=0)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "storageresource"
        verbose_name = _("StorageresourceModel")
        verbose_name_plural = _("StorageresourceModels")
