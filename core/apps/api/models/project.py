from django_core.models import AbstractBaseModel

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectModel(AbstractBaseModel):

    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)
    project_members_count = models.IntegerField(default=0)
    flow = models.ForeignKey("FlowModel", on_delete=models.CASCADE, related_name="projects", null=True, blank=True)
    
    # bots
    bot_for_debug = models.ForeignKey(
        "BotModel", on_delete=models.CASCADE, related_name="debug_projects", null=True, blank=True
    )
    bot_for_release = models.ForeignKey(
        "BotModel", on_delete=models.CASCADE, related_name="release_projects", null=True, blank=True
    )

    bot_is_released = models.BooleanField(default=False)
    bot_is_debug = models.BooleanField(default=False)
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="projects", null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(self):
        return self.objects.create(
            name="mock",
        )

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
    def _create_fake(self):
        return self.objects.create(
            name="mock",
        )

    class Meta:
        db_table = "bot"
        verbose_name = _("BotModel")
        verbose_name_plural = _("BotModels")


class FlowModel(AbstractBaseModel):

    flow = models.JSONField(default=list)
    
    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(self):
        return self.objects.create(
            name="mock",
        )

    class Meta:
        db_table = "flow"
        verbose_name = _("FlowModel")
        verbose_name_plural = _("FlowModels")


class RelaseModel(AbstractBaseModel):
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="relases", null=True, blank=True)
    version = models.CharField(verbose_name=_("version"), max_length=255)
    flow = models.JSONField(default=list)

    
    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(self):
        return self.objects.create(
            name="mock",
        )

    class Meta:
        db_table = "relase"
        verbose_name = _("RelaseModel")
        verbose_name_plural = _("RelaseModels")
