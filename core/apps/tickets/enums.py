from django.db import models
from django.utils.translation import gettext_lazy as _


class TicketStatusEnum(models.TextChoices):
    OPEN = "open", _("Open")
    PENDING = "pending", _("Pending")
    CLOSED = "closed", _("Closed")
