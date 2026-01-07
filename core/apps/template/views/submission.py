from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from decimal import Decimal

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.models.template import TemplateModel
from core.apps.template.serializers.submission import (
    CreateTemplateSubmissionSerializer,
    ListTemplateSubmissionSerializer,
    RetrieveTemplateSubmissionSerializer,
    ApproveTemplateSubmissionSerializer,
    RejectTemplateSubmissionSerializer,
)
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.permissions import IsAdminUser


@extend_schema(tags=["template-submission"])
class TemplateSubmissionView(BaseViewSetMixin, ModelViewSet):
    """
    ViewSet for template submission requests.
    
    Users can submit their projects as templates for approval.
    Admins can approve or reject submissions.
    """
    serializer_class = ListTemplateSubmissionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    action_permission_classes = {
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "create": [IsAuthenticated],
        "partial_update": [IsAuthenticated],
        "destroy": [IsAuthenticated],
        "approve": [IsAdminUser],
        "reject": [IsAdminUser],
    }
    
    action_serializer_class = {
        "list": ListTemplateSubmissionSerializer,
        "retrieve": RetrieveTemplateSubmissionSerializer,
        "create": CreateTemplateSubmissionSerializer,
        "partial_update": CreateTemplateSubmissionSerializer,
        "approve": ApproveTemplateSubmissionSerializer,
        "reject": RejectTemplateSubmissionSerializer,
    }

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            # Admins can see all submissions
            return TemplateSubmissionRequestModel.objects.all().select_related(
                'user', 'project', 'template', 'reviewed_by'
            ).prefetch_related('categories', 'features')
        # Regular users can only see their own submissions
        return TemplateSubmissionRequestModel.objects.filter(
            user=user
        ).select_related(
            'user', 'project', 'template', 'reviewed_by'
        ).prefetch_related('categories', 'features')

    def perform_create(self, serializer):
        """Create a new template submission request"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Only allow updates to pending submissions"""
        instance = self.get_object()
        if instance.status != TemplateSubmissionStatusEnum.PENDING.value:
            raise Response(
                {"detail": "Cannot update non-pending submissions"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if instance.user != self.request.user:
            raise Response(
                {"detail": "Cannot update other users' submissions"},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

    def perform_destroy(self, instance):
        """Only allow deletion of pending submissions by the owner"""
        if instance.status != TemplateSubmissionStatusEnum.PENDING.value:
            raise Response(
                {"detail": "Cannot delete non-pending submissions"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise Response(
                {"detail": "Cannot delete other users' submissions"},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()

    @extend_schema(
        request=ApproveTemplateSubmissionSerializer,
        responses={200: RetrieveTemplateSubmissionSerializer},
        description="Approve a template submission and create a template"
    )
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve a template submission and create a template"""
        submission = self.get_object()
        
        if submission.status != TemplateSubmissionStatusEnum.PENDING.value:
            return Response(
                {"detail": "Only pending submissions can be approved"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ApproveTemplateSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the template from the submission
        template = TemplateModel.objects.create(
            author=submission.user,
            name=submission.name,
            image=submission.image,
            video=submission.video,
            project=submission.project,
            short_description=submission.short_description,
            description=submission.description,
            original_price=submission.original_price,
            discount=Decimal(str(serializer.validated_data.get('discount', 0))),
            discount_type=serializer.validated_data.get('discount_type', 'percent'),
            demo_url=submission.demo_url,
            is_verify=True,
        )
        
        # Set many-to-many relationships
        template.categories.set(submission.categories.all())
        template.features.set(submission.features.all())
        
        # Update submission status
        submission.status = TemplateSubmissionStatusEnum.APPROVED.value
        submission.template = template
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Return updated submission
        response_serializer = RetrieveTemplateSubmissionSerializer(submission)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=RejectTemplateSubmissionSerializer,
        responses={200: RetrieveTemplateSubmissionSerializer},
        description="Reject a template submission"
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Reject a template submission"""
        submission = self.get_object()
        
        if submission.status != TemplateSubmissionStatusEnum.PENDING.value:
            return Response(
                {"detail": "Only pending submissions can be rejected"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RejectTemplateSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update submission status
        submission.status = TemplateSubmissionStatusEnum.REJECTED.value
        submission.rejection_reason = serializer.validated_data['rejection_reason']
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Return updated submission
        response_serializer = RetrieveTemplateSubmissionSerializer(submission)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
