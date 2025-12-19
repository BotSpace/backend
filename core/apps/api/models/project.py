# type: ignore
import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker

from core.apps.api.enums.container import ContainerStatusEnum

User = get_user_model()


class ProjectModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.FileField(upload_to="avatar/", null=True, blank=True)
    avatar_file_id = models.CharField(max_length=200, null=True, blank=True)
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="projects")
    flow = models.JSONField(default=list)
    is_template = models.BooleanField(default=False)

    release_webhook_uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    debug_webhook_uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    # MongoDB credentials - created once per project
    mongo_username = models.CharField(max_length=255, null=True, blank=True)
    mongo_password = models.CharField(max_length=255, null=True, blank=True)
    mongo_database = models.CharField(max_length=255, null=True, blank=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __str__(self):
        return "%s | %s %s" % (self.name, self.owner.first_name, self.owner.last_name)

    @classmethod
    def _create_fake(cls, owner=None):
        instance = baker.make(cls, owner=owner or User._create_fake())
        return instance

    @property
    def release(self):
        return RelaseModel.objects.filter(project_id=self.pk).order_by("id").last()

    def get_mongo_credentials(self):
        """Get MongoDB credentials for this project

        Creates credentials if they don't exist yet.

        Returns:
            Dict with connection_string, database, username, and password
        """
        from core.apps.cms.services.mongo import MongoDBClient
        from django.db import transaction

        # If credentials already exist, return them
        if self.mongo_username and self.mongo_password and self.mongo_database:
            mongo_client = MongoDBClient()
            try:
                connection_string = mongo_client._build_connection_string(
                    self.mongo_username, self.mongo_password, self.mongo_database
                )
            finally:
                mongo_client.close()

            return {
                "username": self.mongo_username,
                "password": self.mongo_password,
                "database": self.mongo_database,
                "connection_string": connection_string,
            }

        # Create new credentials
        mongo_client = MongoDBClient()
        try:
            credentials = mongo_client.create_project_user(self.id)

            # Save credentials to project using update to avoid triggering signals again
            # Use update() instead of save() to avoid transaction conflicts
            type(self).objects.filter(pk=self.pk).update(
                mongo_username=credentials["username"],
                mongo_password=credentials["password"],
                mongo_database=credentials["database"],
            )

            # Refresh instance to get updated values
            self.mongo_username = credentials["username"]
            self.mongo_password = credentials["password"]
            self.mongo_database = credentials["database"]

            return credentials
        finally:
            mongo_client.close()

    class Meta:
        db_table = "project"
        verbose_name = _("ProjectModel")
        verbose_name_plural = _("ProjectModels")


class BotModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    token = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    bot_members_count = models.IntegerField(default=0)

    def __str__(self):
        return str(self.name)

    @classmethod
    def _create_fake(cls):
        return cls.objects.create(
            name="mock",
        )

    class Meta:
        db_table = "bot"
        verbose_name = _("BotModel")
        verbose_name_plural = _("BotModels")


class RelaseModel(AbstractBaseModel):
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="relases")
    version = models.IntegerField(verbose_name=_("version"))
    flow = models.JSONField(default=list)
    service_id = models.CharField(_("service id"), max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=255, default=ContainerStatusEnum.PENDING.value, choices=ContainerStatusEnum.choices
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._status = self.status

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return baker.make(cls, _fill_optional=True, project=ProjectModel._create_fake())

    class Meta:
        db_table = "relase"
        verbose_name = _("RelaseModel")
        verbose_name_plural = _("RelaseModels")


class DebugModel(AbstractBaseModel):
    project = models.OneToOneField("ProjectModel", on_delete=models.CASCADE, related_name="debug")
    flow_hash = models.CharField(max_length=255, null=True, blank=True)
    service_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=255, default=ContainerStatusEnum.STOPPED.value, choices=ContainerStatusEnum.choices
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._status = self.status

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return baker.make(cls, _fill_optional=True)

    class Meta:
        db_table = "debug"
        verbose_name = _("DebugModel")
        verbose_name_plural = _("DebugModels")


class EnviromentModel(AbstractBaseModel):
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="enviroments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(verbose_name=_("name"), max_length=255)
    value = models.CharField(_("value"), max_length=255)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._value = self.value

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        user = baker.make(User)
        return baker.make(
            cls,
            _fill_optional=True,
            project=baker.make(ProjectModel, owner=user),
            user=user,
            key="key",
        )

    class Meta:
        db_table = "enviroment"
        verbose_name = _("EnviromentModel")
        verbose_name_plural = _("EnviromentModels")
        constraints = [models.UniqueConstraint(fields=["key", "project"], name="unique_project_key_project")]
