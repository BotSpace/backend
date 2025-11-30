from django_core.mixins import BaseViewSetMixin
from typing import Any
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models.project import ProjectModel
from core.apps.api.models.resource import ResourceModel
from core.apps.api.serializers.resource.resource import (
    CreateResourceSerializer,
    ListResourceSerializer,
    RetrieveResourceSerializer,
)
from core.apps.api.serializers.resource.used import UsedStatSerializer
from core.apps.api.services.used import UsedService
from core.services.response import success_response


@extend_schema(tags=["used"])
class UsedView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.usedService = UsedService()

    def get_serializer_class(self):
        return UsedStatSerializer

    def get_serializer(self, *args, **kwargs):
        return self.get_serializer_class()(
            *args,
            **kwargs,
            context={"request": self.request},
        )

    def get_queryset(self):
        return ProjectModel.objects.filter(owner=self.request.user)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs.get("project_id"))

    def get(self, request, project_id=None):
        if project_id is None:
            self.usedService.set_mode("user")
            self.usedService.set_user(self.request.user)
        else:
            self.usedService.set_project(self.get_object())
        return Response(
            data=success_response(
                self.get_serializer(instance=self.usedService.get_used()).data, status.HTTP_200_OK
            ).data
        )


@extend_schema(tags=["resource"])
class ResourceView(BaseViewSetMixin, ModelViewSet):
    serializer_class = ListResourceSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {}
    action_serializer_class = {
        "list": ListResourceSerializer,
        "retrieve": RetrieveResourceSerializer,
        "create": CreateResourceSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return ResourceModel.objects.filter(user=self.request.user)
