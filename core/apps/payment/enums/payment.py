from django.db import models


class PaymentMethosEnum(models.TextChoices):
    CLICK = "click"
    PAYME = "payme"
    PAYNET = "paynet"
    UZUM = "uzum"
