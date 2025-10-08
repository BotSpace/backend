from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.models import BotModel, DebugModel, EnviromentModel, ProjectModel, RelaseModel


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=BotModel)
def BotSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=RelaseModel)
def RelaseSignal(sender, instance, created, **kwargs):
    if created:
        RelaseModel.objects.filter(project=instance.project).exclude(pk=instance.pk).update(is_active=False)


@receiver(post_save, sender=DebugModel)
def DebugSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=EnviromentModel)
def EnviromentSignal(sender, instance, created, **kwargs): ...
