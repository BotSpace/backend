# type: ignore
"""
Pricing Plan Models
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from model_bakery import baker
from decimal import Decimal

from core.apps.api.enums.plan import PlanType, PlanStatus


class PlanModel(AbstractBaseModel):
    """Tarif rejasi modeli"""

    # Tarif endi FOYDALANUVCHIGA biriktiriladi (UserSubscription orqali),
    # avvalgi loyiha-asosli model emas. Limitlar foydalanuvchi resurslari:
    # nechta bot yaratishi va oylik AI token sarfi.
    name = models.CharField(verbose_name=_("Nom"), max_length=50, choices=PlanType.choices, unique=True)
    price = models.DecimalField(verbose_name=_("Narx"), max_digits=20, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(verbose_name=_("Tavsif"), null=True, blank=True)
    is_top = models.BooleanField(default=False)
    is_active = models.BooleanField(verbose_name=_("Faol"), default=True)
    order = models.IntegerField(verbose_name=_("Tartib"), default=0)
    # Foydalanuvchi limitlari (enforce qilinadi: can_create_bot, token tracking)
    max_bots = models.IntegerField(
        verbose_name=_("Maksimal botlar soni"), default=1, help_text=_("0 = cheksiz")
    )
    max_tokens = models.BigIntegerField(verbose_name=_("Oylik token limiti"), default=1000000)
    # Deprecated: eski alohida input/output limitlar — faqat migration va tarixiy ma'lumot uchun saqlanadi.
    max_output_tokens = models.BigIntegerField(verbose_name=_("Oylik output token limiti (deprecated)"), default=200000)
    max_input_tokens = models.BigIntegerField(verbose_name=_("Oylik input token limiti (deprecated)"), default=800000)
    features = models.JSONField(verbose_name=_("Xususiyatlar"), default=dict, blank=True)

    def __str__(self):
        return f"{self.get_name_display()} - ${self.price}"

    @classmethod
    def _create_fake(cls):
        return baker.make(cls)

    class Meta:
        db_table = "plan"
        verbose_name = _("Tarif")
        verbose_name_plural = _("Tariflar")
        ordering = ["order"]


class UserSubscription(AbstractBaseModel):
    """Foydalanuvchi tarifi"""

    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(PlanModel, on_delete=models.PROTECT, related_name="user_subscriptions")
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    tokens_used_input = models.BigIntegerField(default=0)
    tokens_used_output = models.BigIntegerField(default=0)
    token_reset_at = models.DateTimeField(auto_now_add=True)
    bots_count = models.IntegerField(default=0)

    class Meta:
        db_table = "user_subscription"
        verbose_name = _("Foydalanuvchi tarifi")
        verbose_name_plural = _("Foydalanuvchi tariflari")

    def __str__(self):
        return f"{self.user} - {self.plan.get_name_display()}"

    def is_token_limit_exceeded(self) -> bool:
        return self.tokens_remaining() <= 0

    def can_create_bot(self) -> bool:
        if self.plan.max_bots == 0:
            return True
        return self.bots_count < self.plan.max_bots

    def tokens_remaining(self) -> int:
        token_limit = self.plan.max_tokens
        tokens_used = self.tokens_used_input + self.tokens_used_output
        return max(0, token_limit - tokens_used)

    @classmethod
    def _create_fake(cls):
        from core.apps.accounts.models import User

        user = User._create_fake()
        plan = PlanModel.objects.filter(name=PlanType.FREE).first() or PlanModel._create_fake()
        return baker.make(cls, user=user, plan=plan)
