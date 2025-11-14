from django.db import models


class TemplateTypeEnum(models.TextChoices):
    PERCENT = "percent"
    AMOUNT = "amount"
