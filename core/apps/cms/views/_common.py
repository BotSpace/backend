"""Shared helpers for cms views."""

from __future__ import annotations

from rest_framework.exceptions import NotFound

from core.apps.cms.models import Collection


def resolve_project(value):
    """Return ProjectModel by integer pk OR by UUID string.

    Always returns a real project instance so callers can safely use
    ``project.pk`` (integer) for MongoDB db names and FK filters.
    Returns None when not found (deleted_at is ignored intentionally —
    callers that need soft-delete check should inspect the result).
    """
    import uuid as _uuid

    from core.apps.api.models import ProjectModel

    raw = str(value).strip()
    try:
        int_pk = int(raw)
        return ProjectModel.objects.filter(pk=int_pk).first()
    except ValueError:
        pass
    # Guard against malformed UUID strings — Django would raise on filter().
    try:
        _uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None
    return ProjectModel.objects.filter(uuid=raw).first()


def get_project_or_404(project_id):
    project = resolve_project(project_id)
    if project is None:
        raise NotFound("Project not found")
    return project


def get_collection_or_404(*, project_id, name: str | None = None, pk: int | None = None) -> Collection:
    # Resolve project_id (may be UUID or int string) to integer FK.
    project = get_project_or_404(project_id)
    qs = Collection.objects.filter(project_id=project.pk, deleted_at__isnull=True)
    if name is not None:
        coll = qs.filter(name=name).first()
    elif pk is not None:
        coll = qs.filter(pk=pk).first()
    else:
        coll = None
    if coll is None:
        raise NotFound("Collection not found")
    return coll
