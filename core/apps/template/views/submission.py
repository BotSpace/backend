from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError, PermissionDenied

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.serializers.submission import (
    CreateTemplateSubmissionSerializer,
    ListTemplateSubmissionSerializer,
    RetrieveTemplateSubmissionSerializer,
)
from core.apps.template.enums.template import TemplateSubmissionStatusEnum


@extend_schema(tags=["template-submission"])
class TemplateSubmissionView(BaseViewSetMixin, ModelViewSet):
    """
    ViewSet for template submission requests.

    Users can submit their projects as templates for approval.
    Admins can approve or reject submissions via Django admin panel.
    """

    serializer_class = ListTemplateSubmissionSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "create": [IsAuthenticated],
        "partial_update": [IsAuthenticated],
        "destroy": [IsAuthenticated],
    }

    action_serializer_class = {
        "list": ListTemplateSubmissionSerializer,
        "retrieve": RetrieveTemplateSubmissionSerializer,
        "create": CreateTemplateSubmissionSerializer,
        "partial_update": CreateTemplateSubmissionSerializer,
    }

    def get_queryset(self):
        user = self.request.user
        # Users can only see their own submissions
        return (
            TemplateSubmissionRequestModel.objects.filter(user=user)
            .select_related("user", "project", "template", "reviewed_by")
            .prefetch_related("categories", "features")
        )

    def perform_create(self, serializer):
        """Create a new template submission request"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Only allow updates to pending submissions"""
        instance = self.get_object()
        if instance.status != TemplateSubmissionStatusEnum.PENDING.value:
            raise ValidationError("Cannot update non-pending submissions")
        if instance.user != self.request.user:
            raise PermissionDenied("Cannot update other users' submissions")
        serializer.save()

    def perform_destroy(self, instance):
        """Only allow deletion of pending submissions by the owner"""
        if instance.status != TemplateSubmissionStatusEnum.PENDING.value:
            raise ValidationError("Cannot delete non-pending submissions")
        if instance.user != self.request.user:
            raise PermissionDenied("Cannot delete other users' submissions")
        instance.delete()
