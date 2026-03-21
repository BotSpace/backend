from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.apps.cms.models import CollectionModel
from core.apps.cms.services.mongo import delete_collection


@receiver(post_save, sender=CollectionModel)
def CollectionSignal(sender, instance, created, **kwargs): ...


@receiver(post_delete, sender=CollectionModel)
def collection_delete_signal(sender, instance, **kwargs):
    """Delete MongoDB collection when CollectionModel is deleted"""
    if getattr(settings, "TESTING", False):
        return
    delete_collection(instance)
