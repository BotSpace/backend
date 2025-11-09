from django.db import models

from core.apps.api.enums import ButtonTypeEnum, MessageTypeEnum, MessageStatusEnum


class MessageModel(models.Model):
    project = models.ForeignKey("ProjectModel", on_delete=models.CASCADE)
    caption = models.TextField()
    message_type = models.CharField(choices=MessageTypeEnum.choices, default=MessageTypeEnum.TEXT, max_length=100)
    file = models.FileField(upload_to="message")
    button_type = models.CharField(choices=ButtonTypeEnum.choices, default=ButtonTypeEnum.REPLY, max_length=100)
    buttons = models.JSONField()

    total = models.BigIntegerField(default=0)
    done = models.BigIntegerField(default=0)
    fail = models.BigIntegerField(default=0)
    status = models.CharField(choices=MessageStatusEnum.choices, default=MessageStatusEnum.PROGRESS, max_length=100)

    class Meta:
        db_table = "message"
        verbose_name = "message"
        verbose_name_plural = "messages"