# type: ignore
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.projects import AdminProjectSerializer
from core.apps.administration.services import log_admin_action
from core.apps.api.models.project import ProjectModel


class AdminProjectsView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminProjectSerializer

    def get_queryset(self):
        qs = ProjectModel.objects.select_related("owner").order_by("-id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(username__icontains=search)
                | Q(owner__phone__icontains=search)
            )
        owner = self.request.query_params.get("owner", "").strip()
        if owner.isdigit():
            qs = qs.filter(owner_id=int(owner))
        return qs

    def perform_destroy(self, instance):
        log_admin_action(
            actor=self.request.user,
            action="project.delete",
            target=instance,
            before={"name": instance.name, "owner_id": instance.owner_id},
            request=self.request,
        )
        instance.delete()
