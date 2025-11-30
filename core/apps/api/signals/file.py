from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.apps.api.models import FileModel
from django.core.files.storage import default_storage


@receiver(post_save, sender=FileModel)
def FileSignal(sender, instance, created, **kwargs): ...


@receiver(post_delete, sender=FileModel)
def file_delete_signal(sender, instance, *args, **kwargs):
    default_storage.delete(instance.file.name)
