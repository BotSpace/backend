# type: ignore
"""
Pricing Plan Enums
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class PlanType(models.TextChoices):
    """Tarif turlari"""
    FREE = "free", _("Bepul")
    START = "start", _("Start")
    PRO = "pro", _("Pro")
    ENTERPRISE = "enterprise", _("Enterprise")


class PlanStatus(models.TextChoices):
    """Tarif holati"""
    ACTIVE = "active", _("Faol")
    SUSPENDED = "suspended", _("To'xtatilgan")
    GRACE_PERIOD = "grace_period", _("Imkoniyat muddati")  # 3 kun
    CANCELLED = "cancelled", _("Bekor qilingan")
