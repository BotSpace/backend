from django.db import models


class WithdrawalStatusEnum(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
