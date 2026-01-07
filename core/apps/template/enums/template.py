from django.db import models


class DiscountTypeEnum(models.TextChoices):
    PERCENT = "percent"
    AMOUNT = "amount"


class TemplateSubmissionStatusEnum(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
