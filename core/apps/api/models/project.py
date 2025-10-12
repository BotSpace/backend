from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.api.enums.container import ContainerStatusEnum

User = get_user_model()


class ProjectModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)
    project_members_count = models.IntegerField(default=0)
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="projects", null=True, blank=True)
    flow = models.JSONField(default=list)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls, owner=None):
        instance = cls.objects.create(
            name="Mock Project",
            description="This is a static fake description.",
            username="mockuser",
            avatar="https://example.com/avatar.png",
            project_members_count=3,
            owner=owner or User._create_fake(),  # type: ignore
        )
        DebugModel.objects.create(project=instance)
        return instance

    @property
    def release(self):
        return RelaseModel.objects.filter(project_id=self.pk).order_by("id").last()

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
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="relases", null=True, blank=True)
    version = models.IntegerField(verbose_name=_("version"))
    flow = models.JSONField(default=list)
    service_id = models.CharField(_("service id"), max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=255, default=ContainerStatusEnum.PENDING.value, choices=ContainerStatusEnum.choices
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return cls.objects.create(
            project=ProjectModel._create_fake(),
            version=1,
            flow=[
                {"step": "init", "action": "initialize release"},
                {"step": "deploy", "action": "deploy release"},
                {"step": "verify", "action": "verify release"},
            ],
            service_id="release123",
        )

    class Meta:
        db_table = "relase"
        verbose_name = _("RelaseModel")
        verbose_name_plural = _("RelaseModels")


class DebugModel(AbstractBaseModel):
    project = models.OneToOneField("ProjectModel", on_delete=models.CASCADE, related_name="debug")
    flow_hash = models.CharField(max_length=255, null=True, blank=True)
    service_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=255, default=ContainerStatusEnum.PENDING.value, choices=ContainerStatusEnum.choices
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return cls.objects.create(
            project=ProjectModel._create_fake(),
        )

    class Meta:
        db_table = "debug"
        verbose_name = _("DebugModel")
        verbose_name_plural = _("DebugModels")


class EnviromentModel(AbstractBaseModel):
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="enviroments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(verbose_name=_("name"), max_length=255)
    value = models.CharField(_("value"), max_length=255)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls):
        return cls.objects.create(
            key="mok",
            value="value",
            user=User._create_fake(),  # type: ignore
            project=ProjectModel._create_fake(),
        )

    class Meta:
        db_table = "enviroment"
        verbose_name = _("EnviromentModel")
        verbose_name_plural = _("EnviromentModels")
        constraints = [models.UniqueConstraint(fields=["key", "project"], name="unique_project_key_project")]
