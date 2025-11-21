import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import ProjectModel, RelaseModel
from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.enviroment import project_enviroment
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models.cms import CollectionModel, FieldModel
from core.apps.api.tasks.bot import sync_bot


@receiver(post_save, sender=ProjectModel)
def ProjectSignal(sender, instance, created, **kwargs):
    if created:
        try:
            if not DebugModel.objects.filter(project=instance).exists():
                DebugModel.objects.create(project=instance)
        except Exception as e:
            logging.error(e)
            pass
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
                FieldModel(collection=collection, name="created_at", type=FieldType.DATETIME.value, required=True),
            ]
        )
        logging.info(
            "Project uchun collection yaratildi collection=%s project=%s user=%s",
            "users",
            instance.name,
            instance.owner,
        )


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
            [*list(project_enviroment(instance.project.id)), "IS_RELEASE=true"],
        )
        instance.service_id = service.id
        instance.status = ContainerStatusEnum.INIT.value
        instance.save()


@receiver(post_save, sender=EnviromentModel)
def EnviromentSignal(sender, instance: EnviromentModel, created, **kwargs):
    if instance.key == "RELEASE_BOT_TOKEN" and instance._value != instance.value:
        sync_bot.delay()
