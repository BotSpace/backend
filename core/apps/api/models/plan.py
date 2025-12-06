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

    name = models.CharField(verbose_name=_("Nom"), max_length=50, choices=PlanType.choices, unique=True)
    price = models.DecimalField(verbose_name=_("Narx"), max_digits=20, decimal_places=2, default=Decimal("0.00"))
    max_users = models.IntegerField(verbose_name=_("Maksimal foydalanuvchilar soni"), default=100)
    powered_by_botmother = models.BooleanField(
        verbose_name=_("Powered by BotMother"), default=True, help_text=_("Botda 'Powered by BotMother' ko'rsatiladi")
    )
    custom_domain = models.BooleanField(verbose_name=_("Custom domain"), default=False)
    priority_support = models.BooleanField(verbose_name=_("Priority support"), default=False)
    description = models.TextField(verbose_name=_("Tavsif"), null=True, blank=True)
    is_active = models.BooleanField(verbose_name=_("Faol"), default=True)
    order = models.IntegerField(verbose_name=_("Tartib"), default=0)

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


class ProjectPlanModel(AbstractBaseModel):
    """Proyekt tariflari"""

    project = models.OneToOneField("api.ProjectModel", on_delete=models.CASCADE, related_name="plan_subscription")
    plan = models.ForeignKey(PlanModel, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        verbose_name=_("Holat"), max_length=20, choices=PlanStatus.choices, default=PlanStatus.ACTIVE
    )
    current_users = models.IntegerField(verbose_name=_("Joriy foydalanuvchilar"), default=0)
    limit_exceeded_at = models.DateTimeField(
        verbose_name=_("Limit oshgan sana"),
        null=True,
        blank=True,
        help_text=_("Foydalanuvchilar soni limitdan oshgan sana"),
    )
    grace_period_notified = models.BooleanField(verbose_name=_("Ogohlantirish yuborildi"), default=False)
    started_at = models.DateTimeField(verbose_name=_("Boshlangan sana"), auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name=_("Tugash sanasi"), null=True, blank=True)

    def __str__(self):
        return f"{self.project.name} - {self.plan.get_name_display()}"

    def is_limit_exceeded(self) -> bool:
        """Check if user limit is exceeded"""
        return self.current_users > self.plan.max_users

    def can_add_user(self) -> bool:
        """Check if can add new user"""
        return self.current_users < self.plan.max_users

    @classmethod
    def _create_fake(cls):
        from core.apps.api.models import ProjectModel

        return baker.make(
            cls, project=ProjectModel._create_fake(), plan=PlanModel.objects.first() or PlanModel._create_fake()
        )

    class Meta:
        db_table = "project_plan"
        verbose_name = _("Proyekt tarifi")
        verbose_name_plural = _("Proyekt tariflari")
