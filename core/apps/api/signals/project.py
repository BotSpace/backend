from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import BotModel, DebugModel, EnviromentModel, ProjectModel, RelaseModel
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.enviroment import project_enviroment


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=BotModel)
def BotSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=RelaseModel)
def RelaseSignal(sender, instance, created, **kwargs):
    if created:
        releases = RelaseModel.objects.filter(
            project=instance.project, status__in=[ContainerStatusEnum.INIT.value, ContainerStatusEnum.RUNNING.value]
        )
        for release in releases:
            remove_service(release.service_id)
            release.status = ContainerStatusEnum.STOPPING.value
            release.save()
        service = deploy_service(
            "release",
            instance.flow,
            "%s_%s" % (instance.project.pk, instance.version),
            list(project_enviroment(instance.project.id)),
        )
        instance.service_id = service.id
        instance.status = ContainerStatusEnum.INIT.value
        instance.save()


@receiver(post_save, sender=DebugModel)
def DebugSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=EnviromentModel)
def EnviromentSignal(sender, instance, created, **kwargs): ...
