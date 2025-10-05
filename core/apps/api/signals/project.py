from core.apps.api.models import BotModel, ProjectModel
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=BotModel)
def BotSignal(sender, instance, created, **kwargs): ...
