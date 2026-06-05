from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel
from django.contrib.auth import get_user_model
from model_bakery import baker

from core.apps.shared.validators import (
    image_extension_validator,
    validate_image_size,
    validate_video_size,
    video_extension_validator,
)
from core.apps.template.enums.template import TemplateSubmissionStatusEnum

User = get_user_model()


class TemplateSubmissionRequestModel(AbstractBaseModel):
    """Model for users to submit template creation requests"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="template_submissions",
        verbose_name=_("user")
    )
    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.CASCADE,
        verbose_name=_("project"),
        help_text=_("Project to be converted into a template")
    )
    name = models.CharField(
        verbose_name=_("template name"),
        max_length=255
    )
    short_description = models.TextField(
        verbose_name=_("short description")
    )
    description = models.TextField(
        verbose_name=_("description")
    )
    image = models.ImageField(
        verbose_name=_("image"),
        upload_to="template-submissions/",
        null=True,
        blank=True,
        validators=[image_extension_validator, validate_image_size],
    )
    video = models.FileField(
        upload_to="template-submission-videos/",
        null=True,
        blank=True,
        verbose_name=_("video"),
        validators=[video_extension_validator, validate_video_size],
    )
    demo_url = models.URLField(
        null=True,
        blank=True,
        verbose_name=_("demo URL")
    )
    original_price = models.DecimalField(
        verbose_name=_("original price"),
        max_digits=20,
        decimal_places=2
    )
    categories = models.ManyToManyField(
        "TemplateCategoryModel",
        blank=True,
        verbose_name=_("categories")
    )
    features = models.ManyToManyField(
        "TemplateFeatureModel",
        blank=True,
        verbose_name=_("features")
    )
    status = models.CharField(
        max_length=255,
        choices=TemplateSubmissionStatusEnum.choices,
        default=TemplateSubmissionStatusEnum.PENDING.value,
        verbose_name=_("status")
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("rejection reason"),
        help_text=_("Reason for rejection if status is rejected")
    )
    template = models.ForeignKey(
        "TemplateModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
        verbose_name=_("template"),
        help_text=_("Created template if approved")
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_submissions",
        verbose_name=_("reviewed by")
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("reviewed at")
    )
    required_envs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("required envs"),
        help_text=_('List of required env vars. Format: [{"key": "ADMIN_CHAT_ID", "description": "..."}]'),
    )

    def __str__(self):
        return f"{self.name} - {self.user.phone} ({self.status})"

    @classmethod
    def _baker(cls):
        return baker.make(cls)

    class Meta:
        db_table = "template_submission_request"
        verbose_name = _("Template Submission Request")
        verbose_name_plural = _("Template Submission Requests")
        ordering = ["-created_at"]
