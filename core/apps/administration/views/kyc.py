# type: ignore
"""Admin KYC Verifications — pasport/rasm/ma'lumotnomani tasdiqlash/rad etish.

Tasdiqlashda foydalanuvchining ``kyc_verified_at`` o'rnatiladi va keyingi
barcha pul yechishlar ochiladi.
"""

from django.db import transaction
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.accounts.choices.verification import VerificationStatusChoice
from core.apps.accounts.models.verification import UserVerificationModel
from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.kyc import (
    AdminKycApproveSerializer,
    AdminKycRejectSerializer,
    AdminKycSerializer,
)
from core.apps.administration.services import log_admin_action


class AdminKycVerificationView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminKycSerializer

    def get_queryset(self):
        qs = (
            UserVerificationModel.objects
            .select_related("user", "reviewed_by")
            .order_by("-id")
        )
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        serializer = AdminKycApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                UserVerificationModel.objects
                .select_for_update()
                .select_related("user")
                .get(pk=pk)
            )
            if target.status != VerificationStatusChoice.PENDING.value:
                return Response(
                    {"detail": f"So'rov allaqachon `{target.status}` holatida."},
                    status=status.HTTP_409_CONFLICT,
                )
            now = timezone.now()
            target.status = VerificationStatusChoice.APPROVED.value
            target.reviewed_by = request.user
            target.reviewed_at = now
            target.save()
            user = target.user
            user.kyc_verified_at = now
            user.save(update_fields=["kyc_verified_at", "updated_at"])
            log_admin_action(
                actor=request.user,
                action="kyc.approve",
                target=target,
                before={"status": VerificationStatusChoice.PENDING.value},
                after={"status": target.status},
                note=serializer.validated_data.get("note", "")[:255],
                request=request,
            )
        target.refresh_from_db()
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        serializer = AdminKycRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                UserVerificationModel.objects
                .select_for_update()
                .get(pk=pk)
            )
            if target.status != VerificationStatusChoice.PENDING.value:
                return Response(
                    {"detail": f"So'rov allaqachon `{target.status}` holatida."},
                    status=status.HTTP_409_CONFLICT,
                )
            before = {"status": target.status}
            target.status = VerificationStatusChoice.REJECTED.value
            target.rejection_reason = serializer.validated_data["rejection_reason"]
            target.reviewed_by = request.user
            target.reviewed_at = timezone.now()
            target.save()
            log_admin_action(
                actor=request.user,
                action="kyc.reject",
                target=target,
                before=before,
                after={"status": target.status, "rejection_reason": target.rejection_reason},
                request=request,
            )
        return Response(self.get_serializer(target).data)
