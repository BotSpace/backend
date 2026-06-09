from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

from core.apps.shared.validators import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    validate_document_size,
)
from core.apps.tickets.enums import TicketStatusEnum

User = get_user_model()

# Murojaatga rasm yoki hujjat biriktirish mumkin.
ticket_attachment_validator = FileExtensionValidator(IMAGE_EXTENSIONS + DOCUMENT_EXTENSIONS)


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
    attachment = models.FileField(
        verbose_name=_("attachment"),
        upload_to="tickets/",
        null=True,
        blank=True,
        validators=[ticket_attachment_validator, validate_document_size],
        help_text=_("Ixtiyoriy fayl (rasm yoki hujjat)"),
    )
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
