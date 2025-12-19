from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.models.message import MessageModel
from core.apps.api.tasks import send_message


@receiver(post_save, sender=MessageModel)
def message_post_save(sender, instance, created, **kwargs):
    if created:
        send_message.delay(instance.pk)