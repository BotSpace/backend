from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.template.models import TemplateOrderModel


@receiver(post_save, sender=TemplateOrderModel)
def OrderSignal(sender, instance, created, **kwargs): ...
