from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel


class TemplateVersionModel(AbstractBaseModel):
    """Append-only snapshot of a template's spec at a point in time.

    A new row is written on template create, spec edit, resync and rollback.
    Rollback itself is a new (higher) version whose spec equals an older one,
    so the history is never rewritten.
    """

    template = models.ForeignKey(
        "TemplateModel", on_delete=models.CASCADE, related_name="versions"
    )
    version = models.PositiveIntegerField(verbose_name=_("version"))
    spec = models.JSONField(default=dict, blank=True, verbose_name=_("spec"))
    note = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="template_versions",
    )

    def __str__(self):
        return "%s v%s" % (self.template_id, self.version)

    class Meta:
        db_table = "template_version"
        verbose_name = _("TemplateVersionModel")
        verbose_name_plural = _("TemplateVersionModels")
        unique_together = ("template", "version")
        ordering = ["-version"]
