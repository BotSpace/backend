import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.shared.models import SoftDeleteModel
from core.apps.shared.validators import image_extension_validator, validate_avatar_size

User = get_user_model()


class ProjectModel(SoftDeleteModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.FileField(
        upload_to="avatar/",
        null=True,
        blank=True,
        validators=[image_extension_validator, validate_avatar_size],
    )
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
        """Latest release for this project.

        When the queryset prefetches ``relases`` with ``Prefetch(..., to_attr=
        "prefetched_relases")``, that cached list is used (no extra query).
        Otherwise falls back to a single SQL query.
        """
        cached = getattr(self, "_prefetched_release", None)
        if cached is not None:
            return cached or None
        prefetched_list = getattr(self, "prefetched_relases", None)
        if prefetched_list is not None:
            return prefetched_list[0] if prefetched_list else None
        return RelaseModel.objects.filter(project_id=self.pk).order_by("-id").first()

    def get_mongo_credentials(self):
        """Get-or-create per-project MongoDB credentials.

        Thin wrapper around
        :class:`core.apps.cms_legacy.services.credentials.ProjectMongoCredentialsService`
        kept for call-site compatibility.
        """
        from core.apps.cms_legacy.services.credentials import project_mongo_credentials

        creds = project_mongo_credentials.get_or_create(self.pk)
        self.mongo_username = creds.username
        self.mongo_password = creds.password
        self.mongo_database = creds.database
        return {
            "username": creds.username,
            "password": creds.password,
            "database": creds.database,
            "connection_string": creds.connection_string,
        }

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
