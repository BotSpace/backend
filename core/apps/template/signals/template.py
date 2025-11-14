from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.template.models import TemplateModel, UserTemplateModel


@receiver(post_save, sender=TemplateModel)
def TemplateSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=UserTemplateModel)
def UsertemplateSignal(sender, instance, created, **kwargs): ...
