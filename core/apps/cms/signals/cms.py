from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.cms.models import CollectionModel


@receiver(post_save, sender=CollectionModel)
def CollectionSignal(sender, instance, created, **kwargs): ...
