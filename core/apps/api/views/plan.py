# type: ignore
"""
Plan API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from core.apps.api.models import PlanModel, ProjectPlanModel, ProjectModel
from core.apps.api.serializers.plan import (
    PlanSerializer,
    ProjectPlanSerializer,
    ProjectPlanUpgradeSerializer
)
from core.apps.api.enums.plan import PlanStatus


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Tariflarni ko'rish API
    
    list: Barcha aktiv tariflarni olish
    retrieve: Bitta tarifni ko'rish
    """
    queryset = PlanModel.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = []  # Public endpoint
    
    def get_queryset(self):
        """Filter only active plans, ordered by price"""
        return PlanModel.objects.filter(is_active=True).order_by('order')


class ProjectPlanViewSet(viewsets.ViewSet):
    """
    Proyekt tariflari boshqaruvi
    
    get_current: Joriy proyekt tarifini olish
    upgrade: Tarifni yangilash
    """
    permission_classes = [IsAuthenticated]
    
    def get_current(self, request, project_pk=None):
        """
        Proyektning joriy tarifini olish
        
        GET /api/projects/{project_id}/plan/
        """
        project = get_object_or_404(
            ProjectModel,
            pk=project_pk,
            owner=request.user
        )
        
        try:
            project_plan = ProjectPlanModel.objects.select_related('plan').get(
                project=project
            )
            serializer = ProjectPlanSerializer(project_plan)
            return Response(serializer.data)
        
        except ProjectPlanModel.DoesNotExist:
            return Response(
                {
                    'error': 'No plan assigned to this project',
                    'detail': 'Please contact support'
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def upgrade(self, request, project_pk=None):
        """
        Proyekt tarifini yangilash
        
        POST /api/projects/{project_id}/plan/upgrade/
        Body: {"plan_id": 2}
        """
        project = get_object_or_404(
            ProjectModel,
            pk=project_pk,
            owner=request.user
        )
        
        try:
            project_plan = ProjectPlanModel.objects.select_related('plan').get(
                project=project
            )
        except ProjectPlanModel.DoesNotExist:
            return Response(
                {'error': 'No plan assigned to this project'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate upgrade request
        serializer = ProjectPlanUpgradeSerializer(
            data=request.data,
            context={'project_plan': project_plan}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform upgrade
        new_plan = serializer.validated_data['plan']
        old_plan = project_plan.plan
        
        project_plan.plan = new_plan
        
        # Reset status if upgrading from suspended/grace period
        if project_plan.status in [PlanStatus.SUSPENDED, PlanStatus.GRACE_PERIOD]:
            # Check if new plan can handle current users
            if new_plan.max_users >= project_plan.current_users:
                project_plan.status = PlanStatus.ACTIVE
                project_plan.limit_exceeded_at = None
                project_plan.grace_period_notified = False
        
        project_plan.save()
        
        # Log upgrade
        import logging
        logging.info(
            f"Project {project.id} plan upgraded: "
            f"{old_plan.get_name_display()} → {new_plan.get_name_display()}"
        )
        
        # Return updated plan
        response_serializer = ProjectPlanSerializer(project_plan)
        return Response(
            {
                'message': 'Plan successfully upgraded',
                'previous_plan': old_plan.get_name_display(),
                'new_plan': new_plan.get_name_display(),
                'data': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    def usage_stats(self, request, project_pk=None):
        """
        Proyekt foydalanish statistikasi
        
        GET /api/projects/{project_id}/plan/usage/
        """
        project = get_object_or_404(
            ProjectModel,
            pk=project_pk,
            owner=request.user
        )
        
        try:
            project_plan = ProjectPlanModel.objects.select_related('plan').get(
                project=project
            )
            
            usage_percentage = (
                (project_plan.current_users / project_plan.plan.max_users * 100)
                if project_plan.plan.max_users > 0
                else 0
            )
            
            return Response({
                'current_users': project_plan.current_users,
                'max_users': project_plan.plan.max_users,
                'usage_percentage': round(usage_percentage, 2),
                'limit_exceeded': project_plan.is_limit_exceeded(),
                'can_add_user': project_plan.can_add_user(),
                'status': project_plan.status,
                'plan_name': project_plan.plan.get_name_display(),
            })
        
        except ProjectPlanModel.DoesNotExist:
            return Response(
                {'error': 'No plan assigned'},
                status=status.HTTP_404_NOT_FOUND
            )
