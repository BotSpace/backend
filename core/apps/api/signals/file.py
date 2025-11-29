from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.models import FileModel


@receiver(post_save, sender=FileModel)
def FileSignal(sender, instance, created, **kwargs): ...
