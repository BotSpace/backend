"""Shared helpers for cms views."""

from __future__ import annotations

from rest_framework.exceptions import NotFound

from core.apps.cms.models import Collection


def get_project_or_404(project_id):
    from core.apps.api.models import ProjectModel

    project = ProjectModel.objects.filter(pk=project_id).first()
    if project is None:
        raise NotFound("Project not found")
    return project


def get_collection_or_404(*, project_id, name: str | None = None, pk: int | None = None) -> Collection:
    qs = Collection.objects.filter(project_id=project_id, deleted_at__isnull=True)
    if name is not None:
        coll = qs.filter(name=name).first()
    elif pk is not None:
        coll = qs.filter(pk=pk).first()
    else:
        coll = None
    if coll is None:
        raise NotFound("Collection not found")
    return coll
