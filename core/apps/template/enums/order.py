from django.db import models


class TemplateOrderStatusEnum(models.TextChoices):
    PENDING = "pending"
    CONFIRM = "confirm"
    CANCEL = "cancel"
