# type: ignore
"""Admin monitoring — barcha loyihalarning resurs holati + tarixi.

GET  /api/v1/admin/monitoring/                  → loyihalar jadvali (joriy CPU/RAM/disk),
                                                   user (owner) va loyiha (search) bo'yicha
                                                   filtr, resurs/sana bo'yicha saralash.
GET  /api/v1/admin/monitoring/{id}/history/      → bitta loyihaning tarix chartlari.
"""

from django.db.models import OuterRef, Q, Subquery
from django_core.mixins import BaseViewSetMixin
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.api.models.project import ProjectModel, RelaseModel
from core.apps.api.services.monitoring import (
    fetch_current_usage_by_project,
    get_project_history,
    latest_disk_by_project,
)

_RESOURCE_ORDERINGS = {"cpu", "-cpu", "memory", "-memory", "disk", "-disk"}
_DB_ORDERINGS = {"id", "-id", "created_at", "-created_at", "name", "-name"}


class AdminMonitoringView(BaseViewSetMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    # ponytail: barcha (filtrlangan) loyihalarni xotiraga oladi — platforma ko'lamida
    # qabul qilinadi; loyihalar minglab bo'lsa keyin server-side resurs saralash kerak.

    def _base_queryset(self):
        latest_status = (
            RelaseModel.objects.filter(project=OuterRef("pk")).order_by("-version").values("status")[:1]
        )
        qs = (
            ProjectModel.objects.select_related("owner")
            .annotate(latest_release_status=Subquery(latest_status))
            .filter(deleted_at__isnull=True)
        )
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
        else:
            qs = qs.filter(is_template=False)  # default: shablonlarni yashir
        has_release = p.get("has_release", "").strip()
        if has_release == "true":
            qs = qs.filter(relases__isnull=False).distinct()
        elif has_release == "false":
            qs = qs.filter(relases__isnull=True)
        return qs.order_by("-id")

    def list(self, request):
        qs = self._base_queryset()
        projects = list(qs)

        usage_map, prom_available = fetch_current_usage_by_project()
        disk_map = latest_disk_by_project([p.id for p in projects])

        rows = []
        for p in projects:
            u = usage_map.get(p.id, {})
            rows.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "username": p.username,
                    "owner_id": p.owner_id,
                    "owner_phone": getattr(p.owner, "phone", None),
                    "owner_name": (
                        f"{p.owner.first_name or ''} {p.owner.last_name or ''}".strip()
                        if p.owner_id
                        else None
                    ),
                    "release_status": getattr(p, "latest_release_status", None),
                    "cpu_cores": u.get("cpu_cores"),
                    "memory_bytes": u.get("memory_bytes"),
                    "disk_bytes": disk_map.get(p.id, 0),
                    "created_at": p.created_at,
                }
            )

        ordering = request.query_params.get("ordering", "").strip()
        if ordering in _RESOURCE_ORDERINGS:
            key = ordering.lstrip("-")
            field = {"cpu": "cpu_cores", "memory": "memory_bytes", "disk": "disk_bytes"}[key]
            rows.sort(key=lambda r: (r.get(field) or 0), reverse=ordering.startswith("-"))
        elif ordering in _DB_ORDERINGS:
            field = ordering.lstrip("-")
            rows.sort(key=lambda r: (r.get(field) or 0) if field != "name" else (r.get("name") or ""),
                      reverse=ordering.startswith("-"))

        page = self.paginate_queryset(rows)
        resp = self.get_paginated_response(page if page is not None else rows)
        resp.data["prometheus_available"] = prom_available
        return resp

    @action(methods=["GET"], detail=True, url_path="history", url_name="history")
    def history(self, request, pk=None):
        range_key = request.query_params.get("range", "24h")
        return Response(get_project_history(int(pk), range_key))
