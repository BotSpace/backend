import logging
import os

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import BotModel, DebugModel, EnviromentModel, ProjectModel, RelaseModel
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.enviroment import project_enviroment
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models.cms import CollectionModel, FieldModel
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs):
    if created:
        collection = CollectionModel.objects.create(
            name="users",
            user=instance.owner,
            project=instance,
        )
        FieldModel.objects.bulk_create(
            [
                FieldModel(collection=collection, name="chat_id", type=FieldType.NUMBER.value, required=True),
                FieldModel(collection=collection, name="first_name", type=FieldType.TEXT.value, required=True),
                FieldModel(collection=collection, name="last_name", type=FieldType.TEXT.value, required=False),
            ]
        )
        logging.info(
            "Project uchun collection yaratildi collection=%s project=%s user=%s",
            "users",
            instance.name,
            instance.owner,
        )


@receiver(post_save, sender=BotModel)
def BotSignal(sender, instance, created, **kwargs): ...


@receiver(post_save, sender=RelaseModel)
def RelaseSignal(sender, instance: RelaseModel, created, **kwargs):
    if created:
        releases = RelaseModel.objects.filter(
            project=instance.project, status__in=[ContainerStatusEnum.INIT.value, ContainerStatusEnum.RUNNING.value]
        )
        for release in releases:
            remove_service(release.service_id)
            release.status = ContainerStatusEnum.STOPPING.value
            release.save()
        service = deploy_service(
            instance.project,
            "release",
            instance.flow,
            "%s_%s" % (instance.project.pk, instance.version),
            list(project_enviroment(instance.project.id)),
        )
        instance.service_id = service.id
        instance.status = ContainerStatusEnum.INIT.value
        instance.save()
    if instance._status != instance.status:
        ws_publish(
            instance.project.owner.id,
            ReleaseContainerStatus(
                project=instance.project.id,
                status=instance.status,
                version=instance.version,
            ),
            EventTypes.RELEASE_STATUS,
        )


@receiver(post_save, sender=DebugModel)
def DebugSignal(sender, instance: DebugModel, created, **kwargs):
    if instance._status != instance.status:
        logging.info(
            "Debug container status o'zgardi instance=%s old_status=%s new_status=%s",
            instance.pk,
            instance._status,
            instance.status,
        )
        ws_publish(
            instance.project.owner.id,
            DebugContainerStatus(project=instance.project.id, status=instance.status),
            EventTypes.DEBUG_STATUS,
        )


@receiver(post_save, sender=EnviromentModel)
def EnviromentSignal(sender, instance, created, **kwargs): ...
