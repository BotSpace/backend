from django.db import models


class DiscountTypeEnum(models.TextChoices):
    PERCENT = "percent"
    AMOUNT = "amount"
