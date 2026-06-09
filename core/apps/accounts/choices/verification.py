from django.db import models
from django.utils.translation import gettext_lazy as _


class VerificationStatusChoice(models.TextChoices):
    """KYC verifikatsiya so'rovining holati."""

    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
