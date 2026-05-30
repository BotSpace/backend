# type: ignore
from django.db.models import Q
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.templates import (
    AdminSubmissionReviewSerializer,
    AdminTemplateSerializer,
    AdminTemplateSubmissionSerializer,
    AdminVerifySerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.template.models import TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel


class AdminTemplatesView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSerializer

    def get_queryset(self):
        qs = TemplateModel.objects.select_related("author").order_by("-id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        verify = self.request.query_params.get("is_verify", "").strip()
        if verify in ("true", "false"):
            qs = qs.filter(is_verify=(verify == "true"))
        return qs

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        target = self.get_object()
        serializer = AdminVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = {"is_verify": target.is_verify}
        target.is_verify = serializer.validated_data["is_verify"]
        target.save(update_fields=["is_verify", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="template.verify",
            target=target,
            before=before,
            after={"is_verify": target.is_verify},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)


class AdminTemplateSubmissionsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSubmissionSerializer

    def get_queryset(self):
        qs = TemplateSubmissionRequestModel.objects.select_related("user").order_by("-id")
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def _review(self, request, pk, new_status: str, action_name: str):
        target = self.get_object()
        serializer = AdminSubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = {"status": target.status}
        target.status = new_status
        # Submission models usually have reviewed_by/reviewed_at — write
        # what's available, ignore missing fields.
        if hasattr(target, "reviewed_by"):
            target.reviewed_by = request.user
        if hasattr(target, "reviewed_at"):
            target.reviewed_at = timezone.now()
        target.save()
        log_admin_action(
            actor=request.user,
            action=f"template_submission.{action_name}",
            target=target,
            before=before,
            after={"status": target.status},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        return self._review(request, pk, TemplateSubmissionStatusEnum.APPROVED.value, "approve")

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        return self._review(request, pk, TemplateSubmissionStatusEnum.REJECTED.value, "reject")
