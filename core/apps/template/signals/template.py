from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.template.models import TemplateModel


@receiver(post_save, sender=TemplateModel)
def TemplateSignal(sender, instance, created, **kwargs): ...
