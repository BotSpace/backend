from django.db import models

from core.apps.api.enums import ButtonTypeEnum, MessageTypeEnum, MessageStatusEnum


class MessageModel(models.Model):
    """Model for storing broadcast messages to bot users"""

    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE, related_name="messages")
    caption = models.TextField(help_text="Message text/caption")
    message_type = models.CharField(
        choices=MessageTypeEnum.choices,
        default=MessageTypeEnum.TEXT,
        max_length=100,
        help_text="Type of message (text, photo, video)",
    )
    file = models.FileField(upload_to="message", null=True, blank=True, help_text="File for photo/video messages")
    file_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="Telegram file_id (cached after first send)"
    )
    button_type = models.CharField(
        choices=ButtonTypeEnum.choices,
        default=ButtonTypeEnum.REPLY,
        max_length=100,
        help_text="Type of keyboard (inline or reply)",
    )
    buttons = models.JSONField(default=list, help_text="2D array of buttons (rows and columns)")

    # Statistics fields
    total = models.BigIntegerField(default=0, help_text="Total number of recipients")
    done = models.BigIntegerField(default=0, help_text="Number of successfully sent messages")
    fail = models.BigIntegerField(default=0, help_text="Number of failed messages")
    status = models.CharField(
        choices=MessageStatusEnum.choices,
        default=MessageStatusEnum.PROGRESS,
        max_length=100,
        help_text="Current status of message sending",
    )

    class Meta:
        db_table = "message"
        verbose_name = "message"
        verbose_name_plural = "messages"

    def __str__(self):
        return f"Message #{self.pk} - {self.message_type} ({self.status})"
