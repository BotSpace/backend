from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.models import ResourceModel, StorageResourceModel


@receiver(post_save, sender=ResourceModel)
def ResourceSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=StorageResourceModel)
def StorageresourceSignal(sender, instance, created, **kwargs): ...
