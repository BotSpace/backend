from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError, PermissionDenied

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel
from core.apps.template.serializers.withdrawal.withdrawal import (
    CreateTemplateWithdrawalSerializer,
    ListTemplateWithdrawalSerializer,
    RetrieveTemplateWithdrawalSerializer,
)
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum


@extend_schema(tags=["template-withdrawal"])
class TemplateWithdrawalView(BaseViewSetMixin, ModelViewSet):
    """
    ViewSet for template withdrawal requests.

    Template authors can request withdrawal of their template earnings.
    Admins can approve or reject requests via Django admin panel.
    """

    serializer_class = ListTemplateWithdrawalSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "create": [IsAuthenticated],
        "destroy": [IsAuthenticated],
    }

    action_serializer_class = {
        "list": ListTemplateWithdrawalSerializer,
        "retrieve": RetrieveTemplateWithdrawalSerializer,
        "create": CreateTemplateWithdrawalSerializer,
    }

    def get_queryset(self):
        user = self.request.user
        # Users can only see their own withdrawal requests
        return TemplateWithdrawalRequestModel.objects.filter(user=user).select_related("user", "reviewed_by")

    def perform_create(self, serializer):
        """Create a new template withdrawal request"""
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        """Only allow deletion of pending withdrawal requests by the owner"""
        if instance.status != WithdrawalStatusEnum.PENDING.value:
            raise ValidationError("Cannot delete non-pending withdrawal requests")
        if instance.user != self.request.user:
            raise PermissionDenied("Cannot delete other users' withdrawal requests")
        instance.delete()
