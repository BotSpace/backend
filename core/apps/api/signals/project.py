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
from core.apps.cms.services.mongo import delete_project_database
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

        # Create MongoDB credentials for this project
        # This should run after transaction commits to avoid conflicts
        # Use on_commit to defer credentials creation
        from django.db import transaction
        from django.conf import settings

        def create_mongo_creds():
            """Deferred MongoDB credentials creation"""
            if not getattr(settings, "TESTING", False):
                try:
                    # Refresh instance to ensure we have latest data
                    fresh_instance = type(instance).objects.get(pk=instance.pk)
                    credentials = fresh_instance.get_mongo_credentials()
                    logging.info(
                        "MongoDB credentials created for project project_id=%s username=%s database=%s",
                        fresh_instance.id,
                        credentials["username"],
                        credentials["database"],
                    )
                except Exception as e:
                    # Skip if MongoDB is unavailable or mocked in tests
                    logging.warning(
                        "Skipped MongoDB credentials creation for project project_id=%s: %s", instance.id, str(e)
                    )

        # Defer credentials creation until after transaction commits
        transaction.on_commit(create_mongo_creds)

        # Create default "users" collection
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

        # Assign default FREE plan to new project
        try:
            from core.apps.api.models import PlanModel, ProjectPlanModel
            from core.apps.api.enums.plan import PlanType, PlanStatus

            # Get or create FREE plan
            free_plan, _ = PlanModel.objects.get_or_create(
                name=PlanType.FREE,
                defaults={
                    "price": 0,
                    "max_users": 100,
                    "powered_by_botmother": True,
                    "description": "Bepul tarif - 100 tagacha foydalanuvchi",
                },
            )

            # Assign plan to project
            ProjectPlanModel.objects.create(project=instance, plan=free_plan, status=PlanStatus.ACTIVE, current_users=0)

            logging.info("Project ga FREE plan biriktirildi project_id=%s", instance.id)
        except Exception as e:
            logging.error("Project ga plan biriktirishda xatolik: project_id=%s error=%s", instance.id, e)


@receiver(post_delete, sender=ProjectModel)
def ProjectDeleteSignal(sender, instance, **kwargs):
    """Delete MongoDB database and user when project is deleted"""
    from core.apps.cms.services.mongo import MongoDBClient

    try:
        # Delete MongoDB database
        mongo_client = MongoDBClient()
        mongo_client.client.drop_database(f"project_{instance.id}")

        # Delete MongoDB user
        mongo_client.delete_project_user(instance.id)

        mongo_client.close()

        logging.info(
            "Project MongoDB database va user o'chirildi project_id=%s project_name=%s",
            instance.id,
            instance.name,
        )
    except Exception as e:
        logging.error("Project database va user o'chirishda xatolik: project_id=%s error=%s", instance.id, e)


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


@receiver(post_save, sender=DebugModel)
def DebugSignal(sender, instance: DebugModel, created, **kwargs):
    """Signal for DebugModel changes - invalidate cache when debug is updated"""
    # Invalidate webhook cache for debug mode
    # Even though debug doesn't use cache, we invalidate to ensure consistency
    invalidate_webhook_cache(instance.project, "debug")


@receiver(post_delete, sender=DebugModel)
def delete_debug(sender, instance, **kwargs):
    remove_service(instance.service_id)


def invalidate_webhook_cache(project: ProjectModel, mode: str):
    """Invalidate webhook cache in Redis when release or debug is updated

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
        elif mode == "debug":
            # Debug mode doesn't use cache, but we invalidate for consistency
            # In case webhook service implementation changes in the future
            cache_key = f"webhook:service:debug:{project.debug_webhook_uuid}"
            redis_client.delete(cache_key)
            logging.info(
                "Webhook cache invalidated for debug project=%s uuid=%s",
                project.id,
                project.debug_webhook_uuid,
            )
    except Exception as e:
        logging.error("Failed to invalidate webhook cache: %s", e)
