from django.contrib.auth import models as auth_models
from django.db import models

from ..choices import RoleChoice
from ..managers import UserManager


class User(auth_models.AbstractUser):
    phone = models.CharField(max_length=255, unique=True, blank=True, null=True, default=None)
    username = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    balance = models.BigIntegerField(default=0)
    template_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    prompt_limit = models.PositiveIntegerField(default=5)
    role = models.CharField(
        max_length=255,
        choices=RoleChoice,
        default=RoleChoice.USER,
    )

    USERNAME_FIELD = "phone"
    objects = UserManager()

    @classmethod
    def _create_fake(cls):
        return cls.objects.get_or_create(
            phone="+1234567890",
            username="mockuser",
        )[0]

    def __str__(self):
        return self.phone or self.email or f"User #{self.pk}"
