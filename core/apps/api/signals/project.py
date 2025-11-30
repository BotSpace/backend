import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import ProjectModel, RelaseModel
from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.enviroment import project_enviroment
from core.apps.api.tasks.bot import sync_bot
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models.cms import CollectionModel, FieldModel
from core.services.redis_service import client as redis_client


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

        # Invalidate webhook cache for this release
        invalidate_webhook_cache(instance.project, "release")


@receiver(post_save, sender=EnviromentModel)
def EnviromentSignal(sender, instance: EnviromentModel, created, **kwargs):
    if instance.key == "RELEASE_BOT_TOKEN" and instance._value != instance.value:
        sync_bot.delay()


@receiver(post_delete, sender=RelaseModel)
def delete_release(sender, instance, **kwargs):
    remove_service(instance.service_id)


@receiver(post_delete, sender=DebugModel)
def delete_debug(sender, instance, **kwargs):
    remove_service(instance.service_id)


def invalidate_webhook_cache(project: ProjectModel, mode: str):
    """Invalidate webhook cache in Redis when release is updated

    Args:
        project: ProjectModel instance
        mode: 'release' or 'debug'
    """
    try:
        if mode == "release":
            cache_key = f"webhook:service:release:{project.release_webhook_uuid}"
            redis_client.delete(cache_key)
            logging.info(
                "Webhook cache invalidated for release project=%s uuid=%s",
                project.id,
                project.release_webhook_uuid,
            )
        # Debug mode doesn't use cache, so no need to invalidate
    except Exception as e:
        logging.error("Failed to invalidate webhook cache: %s", e)
