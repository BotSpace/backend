# type: ignore
"""Plan CRUD — pricing tier management."""

from rest_framework import serializers as drf_serializers
from rest_framework import viewsets

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.services import log_admin_action
from core.apps.api.models.plan import PlanModel


class _PlanSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = PlanModel
        fields = "__all__"


class AdminPlansView(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = _PlanSerializer
    queryset = PlanModel.objects.all().order_by("id")

    def perform_create(self, serializer):
        instance = serializer.save()
        log_admin_action(
            actor=self.request.user,
            action="plan.create",
            target=instance,
            after=_PlanSerializer(instance).data,
            request=self.request,
        )

    def perform_update(self, serializer):
        before = _PlanSerializer(serializer.instance).data
        instance = serializer.save()
        log_admin_action(
            actor=self.request.user,
            action="plan.update",
            target=instance,
            before=before,
            after=_PlanSerializer(instance).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_admin_action(
            actor=self.request.user,
            action="plan.delete",
            target=instance,
            before=_PlanSerializer(instance).data,
            request=self.request,
        )
        instance.delete()
