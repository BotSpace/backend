# type: ignore
from django.db.models import Q
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.projects import AdminProjectSerializer
from core.apps.administration.services import log_admin_action
from core.apps.api.models.project import ProjectModel


class AdminProjectsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminProjectSerializer

    def get_queryset(self):
        qs = ProjectModel.objects.select_related("owner").order_by("-id")
        p = self.request.query_params
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(username__icontains=search)
                | Q(owner__phone__icontains=search)
            )
        owner = p.get("owner", "").strip()
        if owner.isdigit():
            qs = qs.filter(owner_id=int(owner))
        is_template = p.get("is_template", "").strip()
        if is_template in ("true", "false"):
            qs = qs.filter(is_template=(is_template == "true"))
        has_release = p.get("has_release", "").strip()
        if has_release == "true":
            qs = qs.filter(relases__isnull=False).distinct()
        elif has_release == "false":
            qs = qs.filter(relases__isnull=True)
        created_after = p.get("created_after", "").strip()
        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
        created_before = p.get("created_before", "").strip()
        if created_before:
            qs = qs.filter(created_at__date__lte=created_before)
        ordering = p.get("ordering", "").strip()
        if ordering in ("id", "-id", "created_at", "-created_at", "name", "-name"):
            qs = qs.order_by(ordering)
        return qs

    def retrieve(self, request, *args, **kwargs):
        """Rich detail: project + owner + releases + collections/bot info."""
        from core.apps.api.models.project import RelaseModel  # noqa: WPS433

        pr = self.get_object()
        releases = [
            {
                "id": r.id,
                "version": r.version,
                "status": r.status,
                "service_id": r.service_id,
                "created_at": r.created_at,
                "node_count": len(r.flow) if isinstance(r.flow, list) else len((r.flow or {}).get("nodes", [])),
            }
            for r in RelaseModel.objects.filter(project=pr).order_by("-version")[:50]
        ]
        flow = pr.flow
        node_count = len(flow) if isinstance(flow, list) else len((flow or {}).get("nodes", []))
        data = {
            "id": pr.id,
            "name": pr.name,
            "description": pr.description,
            "username": pr.username,
            "is_template": pr.is_template,
            "owner": {
                "id": pr.owner_id,
                "phone": getattr(pr.owner, "phone", None),
                "email": getattr(pr.owner, "email", None),
            },
            "release_webhook_uuid": str(pr.release_webhook_uuid),
            "debug_webhook_uuid": str(pr.debug_webhook_uuid),
            "mongo_database": pr.mongo_database,
            "current_node_count": node_count,
            "releases": releases,
            "releases_count": len(releases),
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
        }
        return Response(data)

    def perform_destroy(self, instance):
        log_admin_action(
            actor=self.request.user,
            action="project.delete",
            target=instance,
            before={"name": instance.name, "owner_id": instance.owner_id},
            request=self.request,
        )
        instance.delete()
