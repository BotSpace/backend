from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.tickets.enums import TicketStatusEnum

User = get_user_model()


class TicketModel(AbstractBaseModel):
    """Foydalanuvchining support murojaati."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name=_("user"),
    )
    subject = models.CharField(verbose_name=_("subject"), max_length=255)
    message = models.TextField(verbose_name=_("message"))
    status = models.CharField(
        verbose_name=_("status"),
        max_length=32,
        choices=TicketStatusEnum.choices,
        default=TicketStatusEnum.OPEN.value,
        db_index=True,
    )
    admin_reply = models.TextField(
        verbose_name=_("admin reply"),
        null=True,
        blank=True,
        help_text=_("Admin javobi"),
    )

    def __str__(self):
        return f"#{self.pk} {self.subject} ({self.status})"

    class Meta:
        db_table = "support_ticket"
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")
        ordering = ["-created_at"]
