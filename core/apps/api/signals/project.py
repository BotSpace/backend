from core.apps.api.models import BotModel, FlowModel, ProjectModel, RelaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=BotModel)
def BotSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=FlowModel)
def FlowSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=RelaseModel)
def RelaseSignal(sender, instance, created, **kwargs): ...
