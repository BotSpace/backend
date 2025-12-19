from django.db import models

class ButtonTypeEnum(models.TextChoices):
    INLINE = "inline"
    REPLY = "reply"

class MessageTypeEnum(models.TextChoices):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"

class MessageStatusEnum(models.TextChoices):
    PROGRESS = "progress"
    DONE = "done"
    FAILED = "failed"