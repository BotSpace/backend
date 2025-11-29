from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker
import uuid
from django.contrib.auth import get_user_model

from core.apps.api.enums.file import FileTypeEnum


UserModel = get_user_model()


class FileModel(AbstractBaseModel):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    file = models.FileField(upload_to="media/")
    uuid = models.UUIDField(default=uuid.uuid4)
    filesize = models.BigIntegerField(blank=True, null=True)
    filetype = models.CharField(choices=FileTypeEnum.choices, default=FileTypeEnum.FILE.value)

    def __str__(self):
        return str(self.pk)

    def save(self, *args, **kwargs):
        if self.file:
            self.filesize = self.file.size
        super().save(*args, **kwargs)

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "file"
        verbose_name = _("FileModel")
        verbose_name_plural = _("FileModels")
