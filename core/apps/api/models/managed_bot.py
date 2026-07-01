from django.conf import settings
from django.db import models
from django_core.models import AbstractBaseModel


class ManagedBotModel(AbstractBaseModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_bots",
        null=True,
        blank=True,
    )
    tg_bot_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    token_encrypted = models.TextField()
    used = models.BooleanField(default=False)

    def get_token(self) -> str:
        from core.apps.credentials.services import crypto
        return crypto.decrypt(self.token_encrypted)["token"]

    class Meta:
        db_table = "managed_bot"
        verbose_name = "ManagedBotModel"
        verbose_name_plural = "ManagedBotModels"
