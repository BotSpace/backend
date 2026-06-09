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
from core.apps.tickets.enums import TicketSenderEnum, TicketStatusEnum

User = get_user_model()

# Murojaatga rasm yoki hujjat biriktirish mumkin.
ticket_attachment_validator = FileExtensionValidator(IMAGE_EXTENSIONS + DOCUMENT_EXTENSIONS)


class TicketModel(AbstractBaseModel):
    """Foydalanuvchining support murojaati (suhbat sarlavhasi).

    Suhbat mazmuni ``TicketMessageModel`` orqali yuritiladi — foydalanuvchi va
    support ketma-ket yozadi.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name=_("user"),
    )
    subject = models.CharField(verbose_name=_("subject"), max_length=255)
    status = models.CharField(
        verbose_name=_("status"),
        max_length=32,
        choices=TicketStatusEnum.choices,
        default=TicketStatusEnum.OPEN.value,
        db_index=True,
    )

    def __str__(self):
        return f"#{self.pk} {self.subject} ({self.status})"

    class Meta:
        db_table = "support_ticket"
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")
        ordering = ["-created_at"]


class TicketMessageModel(AbstractBaseModel):
    """Murojaat ichidagi bitta xabar (foydalanuvchi yoki admin)."""

    ticket = models.ForeignKey(
        TicketModel,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("ticket"),
    )
    sender = models.CharField(
        verbose_name=_("sender"),
        max_length=16,
        choices=TicketSenderEnum.choices,
        default=TicketSenderEnum.USER.value,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_messages",
        verbose_name=_("author"),
    )
    message = models.TextField(verbose_name=_("message"))
    attachment = models.FileField(
        verbose_name=_("attachment"),
        upload_to="tickets/",
        null=True,
        blank=True,
        validators=[ticket_attachment_validator, validate_document_size],
        help_text=_("Ixtiyoriy fayl (rasm yoki hujjat)"),
    )

    def __str__(self):
        return f"ticket#{self.ticket_id} {self.sender}"

    class Meta:
        db_table = "support_ticket_message"
        verbose_name = _("Ticket Message")
        verbose_name_plural = _("Ticket Messages")
        ordering = ["created_at", "id"]
