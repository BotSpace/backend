from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.models.message import MessageModel
from core.apps.api.tasks import send_message
from core.services import go_worker


@receiver(post_save, sender=MessageModel)
def message_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    if go_worker.enabled():
        go_worker.enqueue("send_message", message_id=instance.pk)
    else:
        send_message.delay(instance.pk)
