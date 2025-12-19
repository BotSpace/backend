from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.payment.models import TransactionModel


@receiver(post_save, sender=TransactionModel)
def TransactionSignal(sender, instance, created, **kwargs): ...
