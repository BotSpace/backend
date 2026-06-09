from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from core.apps.accounts.choices.verification import VerificationStatusChoice
from core.apps.accounts.models.verification import UserVerificationModel
from core.apps.accounts.serializers.verification import (
    CreateVerificationSerializer,
    VerificationSerializer,
)


@extend_schema(tags=["kyc"])
class VerificationView(BaseViewSetMixin, mixins.CreateModelMixin, GenericViewSet):
    """Foydalanuvchining KYC verifikatsiyasi.

    - ``POST /api/v1/kyc/``        — hujjatlarni yuborish (multipart)
    - ``GET  /api/v1/kyc/status/`` — joriy holatni olish
    """

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CreateVerificationSerializer

    action_serializer_class = {
        "create": CreateVerificationSerializer,
        "status": VerificationSerializer,
    }

    def get_queryset(self):
        return UserVerificationModel.objects.filter(user=self.request.user).order_by("-id")

    def create(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "kyc_verified_at", None):
            return Response(
                {"detail": "Siz allaqachon tasdiqlangansiz."},
                status=http_status.HTTP_409_CONFLICT,
            )
        if self.get_queryset().filter(status=VerificationStatusChoice.PENDING.value).exists():
            return Response(
                {"detail": "Sizda tekshiruvdagi so'rov mavjud."},
                status=http_status.HTTP_409_CONFLICT,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, status=VerificationStatusChoice.PENDING.value)
        return Response(
            VerificationSerializer(serializer.instance, context=self.get_serializer_context()).data,
            status=http_status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        latest = self.get_queryset().first()
        return Response(
            {
                "is_verified": bool(getattr(request.user, "kyc_verified_at", None)),
                "verification": (
                    VerificationSerializer(latest, context=self.get_serializer_context()).data if latest else None
                ),
            }
        )
