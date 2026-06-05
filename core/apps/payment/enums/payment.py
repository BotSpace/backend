from django.db import models


class PaymentMethosEnum(models.TextChoices):
    CLICK = "click"
    PAYME = "payme"
    PAYNET = "paynet"
    UZUM = "uzum"


class PaymentOrderStatusEnum(models.TextChoices):
    CREATED = "created", "Yaratildi"
    PAID = "paid", "To'landi"
    CANCELLED = "cancelled", "Bekor qilindi"
    REFUNDED = "refunded", "Qaytarildi"
