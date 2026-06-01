# type: ignore
"""Admin Settings endpoints — list all setting groups + upsert an option value."""

from django_core.mixins import BaseViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.settings import (
    AdminOptionSerializer,
    AdminSettingsSerializer,
    AdminSettingsSetSerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.shared.models.settings import OptionsModel, SettingsModel


class AdminSettingsView(BaseViewSetMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminSettingsSerializer
    pagination_class = None

    def get_queryset(self):
        return SettingsModel.objects.prefetch_related("options").order_by("key")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="set")
    def set(self, request):
        serializer = AdminSettingsSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settings_key = serializer.validated_data["settings_key"]
        option_key = serializer.validated_data["option_key"]
        new_value = serializer.validated_data["value"]

        settings_obj, _ = SettingsModel.objects.get_or_create(
            key=settings_key,
            defaults={"is_public": False, "description": ""},
        )

        option_obj = OptionsModel.objects.filter(
            settings=settings_obj, key=option_key
        ).first()

        before = {"value": option_obj.value} if option_obj else None

        if option_obj is None:
            option_obj = OptionsModel.objects.create(
                settings=settings_obj,
                key=option_key,
                value=new_value,
            )
        else:
            option_obj.value = new_value
            option_obj.save(update_fields=["value"])

        log_admin_action(
            actor=request.user,
            action="settings.set",
            target_type="OptionsModel",
            target_id=f"{settings_key}.{option_key}",
            before=before,
            after={"value": new_value},
            request=request,
        )

        return Response(
            AdminOptionSerializer(option_obj).data,
            status=status.HTTP_200_OK,
        )
