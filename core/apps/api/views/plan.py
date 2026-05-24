# type: ignore
"""
Plan API Views
"""
import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from core.apps.api.models import PlanModel, ProjectPlanModel, ProjectModel
from core.apps.api.serializers.plan import PlanSerializer, ProjectPlanSerializer, ProjectPlanUpgradeSerializer
from core.apps.api.enums.plan import PlanStatus
from django_core.mixins import BaseViewSetMixin
from core.apps.payment.services.balance import subtract_balance
from core.services.response import error_response, success_response


class PlanViewSet(BaseViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Tariflarni ko'rish API

    list: Barcha aktiv tariflarni olish
    retrieve: Bitta tarifni ko'rish
    """

    queryset = PlanModel.objects.filter(is_active=True).order_by("-id")
    serializer_class = PlanSerializer
    permission_classes = []  # Public endpoint

    def get_queryset(self):
        """Filter only active plans, ordered by price"""
        return PlanModel.objects.filter(is_active=True).order_by("order")


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
        project = get_object_or_404(ProjectModel, pk=project_pk, owner=request.user)

        try:
            project_plan = ProjectPlanModel.objects.select_related("plan").get(project=project)
            serializer = ProjectPlanSerializer(project_plan)
            return success_response(serializer.data)
        except ProjectPlanModel.DoesNotExist:
            return error_response({"detail": "Please contact support"}, 404)

    def upgrade(self, request, project_pk=None):
        """
        Proyekt tarifini yangilash

        POST /api/projects/{project_id}/plan/upgrade/
        Body: {"plan_id": 2}
        """
        project = get_object_or_404(ProjectModel, pk=project_pk, owner=request.user)

        try:
            project_plan = ProjectPlanModel.objects.select_related("plan").get(project=project)
        except ProjectPlanModel.DoesNotExist:
            return error_response({"detail": "No plan assigned to this project"}, 404)

        # Validate upgrade request
        serializer = ProjectPlanUpgradeSerializer(data=request.data, context={"project_plan": project_plan})

        if not serializer.is_valid():
            return error_response(serializer.errors, 400)

        # Perform upgrade
        new_plan = serializer.validated_data["plan"]
        months = serializer.validated_data.get("months", 1)
        total_price = serializer.validated_data["total_price"]
        old_plan = project_plan.plan

        if request.user.balance < total_price:
            return error_response({"detail": "Balanceda yetarli mablag' mavjud emas"}, 403)

        project_plan.plan = new_plan

        # Reset status if upgrading from suspended/grace period
        if project_plan.status in [PlanStatus.SUSPENDED, PlanStatus.GRACE_PERIOD]:
            if new_plan.max_users >= project_plan.current_users:
                project_plan.status = PlanStatus.ACTIVE
                project_plan.limit_exceeded_at = None
                project_plan.grace_period_notified = False

        project_plan.started_at = timezone.now()
        project_plan.expires_at = timezone.now() + timedelta(days=months * 30)
        project_plan.save()

        logging.info(
            f"Project {project.id} plan upgraded: "
            f"{old_plan.get_name_display()} → {new_plan.get_name_display()} ({months} oy)"
        )

        response_serializer = ProjectPlanSerializer(project_plan)
        subtract_balance(
            request.user, total_price,
            f"Tarif yangilandi: {new_plan.get_name_display()} ({months} oy)"
        )
        return success_response(
            {
                "message": "Plan successfully upgraded",
                "previous_plan": old_plan.get_name_display(),
                "new_plan": new_plan.get_name_display(),
                "data": response_serializer.data,
            },
            200,
        )

    def usage_stats(self, request, project_pk=None):
        """
        Proyekt foydalanish statistikasi

        GET /api/projects/{project_id}/plan/usage/
        """
        project = get_object_or_404(ProjectModel, pk=project_pk, owner=request.user)

        try:
            project_plan = ProjectPlanModel.objects.select_related("plan").get(project=project)

            usage_percentage = (
                (project_plan.current_users / project_plan.plan.max_users * 100)
                if project_plan.plan.max_users > 0
                else 0
            )
            input_used = project_plan.tokens_used_input
            output_used = project_plan.tokens_used_output
            token_limit = project_plan.token_limit()
            token_used = project_plan.tokens_used()

            return success_response(
                {
                    "current_users": project_plan.current_users,
                    "max_users": project_plan.plan.max_users,
                    "usage_percentage": round(usage_percentage, 2),
                    "limit_exceeded": project_plan.is_limit_exceeded(),
                    "can_add_user": project_plan.can_add_user(),
                    "status": project_plan.status,
                    "plan_name": project_plan.plan.get_name_display(),
                    "ai_token_usage": {
                        "limit": token_limit,
                        "used": token_used,
                        "remaining": max(0, token_limit - token_used),
                        "input_used": input_used,
                        "output_used": output_used,
                        "plan": {
                            "id": project_plan.plan_id,
                            "name": project_plan.plan.name,
                            "display": project_plan.plan.get_name_display(),
                        },
                        "status": project_plan.status,
                        "token_reset_at": project_plan.token_reset_at,
                    },
                }
            )

        except ProjectPlanModel.DoesNotExist:
            return error_response({"detail": "No plan assigned"})
