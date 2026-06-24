import uuid as uuid_lib

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.api.models.project import ProjectModel


class WebhookEndpointModel(AbstractBaseModel):
    """A unique, project-scoped webhook URL bound to a single flow node.

    Minted once per (project, node_id) — a WebhookTrigger node (or a module that
    requests a webhook) gets a stable URL. Incoming requests hit the Go webhook
    service at /api/hook/<token>/; the service resolves the token (via the internal
    resolve endpoint) to the project's release uuid + node_id and forwards to the
    running engine, which fires that node.
    """

    token = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False, db_index=True)
    project = models.ForeignKey(
        ProjectModel, on_delete=models.CASCADE, related_name="webhook_endpoints"
    )
    node_id = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.project_id}:{self.node_id} -> {self.token}"

    class Meta:
        db_table = "webhook_endpoint"
        verbose_name = _("WebhookEndpoint")
        verbose_name_plural = _("WebhookEndpoints")
        unique_together = [("project", "node_id")]
