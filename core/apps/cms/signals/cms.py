from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.apps.cms.models import CollectionModel
from core.apps.cms.services.mongo import delete_collection, get_collection_name


@receiver(post_save, sender=CollectionModel)
def CollectionSignal(sender, instance, created, **kwargs): ...


@receiver(post_delete, sender=CollectionModel)
def collection_delete_signal(sender, instance, **kwargs):
    delete_collection(get_collection_name(instance))
