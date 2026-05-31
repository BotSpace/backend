from __future__ import annotations

from rest_framework import serializers

from core.apps.api.models.project import ProjectModel


class ProjectPkOrUuidField(serializers.PrimaryKeyRelatedField):
    """Writable project FK that accepts either an integer pk OR a UUID string.

    The internal value is always the resolved ``ProjectModel`` instance, so
    downstream validators/queries keep using the integer pk. Representation
    stays the integer pk (PrimaryKeyRelatedField default).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", ProjectModel.objects.all())
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        from core.apps.cms.views._common import resolve_project

        project = resolve_project(data)
        if project is None:
            self.fail("does_not_exist", pk_value=data)
        return project
