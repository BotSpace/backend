from django.db import models
from django.utils.translation import gettext_lazy as _


class ContainerStatusEnum(models.TextChoices):
    PENDING = "pending", _("pending")
    INIT = "initializing", _("initializing")
    RUNNING = "running", _("running")
    STOPPED = "stopped", _("stopped")
    STOPPING = "stopping", _("stopping")
    FAILED = "failed", _("failed")
    SUSPENDED = "suspended", _("suspended")
