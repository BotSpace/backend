from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel


class ModuleModel(AbstractBaseModel):
    slug = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=255, null=True, blank=True)
    github_url = models.CharField(max_length=500, null=True, blank=True)
    image = models.CharField(max_length=500)
    port = models.IntegerField(default=8100)
    auth_token = models.CharField(max_length=500, null=True, blank=True)
    manifest_cache = models.JSONField(null=True, blank=True)
    manifest_fetched_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.slug

    class Meta:
        db_table = "module"
        verbose_name = _("ModuleModel")
        verbose_name_plural = _("ModuleModels")


class ProjectModuleModel(AbstractBaseModel):
    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.CASCADE,
        related_name="project_modules",
    )
    module = models.ForeignKey(
        ModuleModel,
        on_delete=models.CASCADE,
        related_name="project_modules",
    )
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    service_id = models.CharField(max_length=255, null=True, blank=True)
    endpoint = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=50, default="pending")

    def __str__(self):
        return f"{self.project_id}:{self.module.slug}"

    class Meta:
        db_table = "project_module"
        verbose_name = _("ProjectModuleModel")
        verbose_name_plural = _("ProjectModuleModels")
        unique_together = (("project", "module"),)
