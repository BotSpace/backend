"""Template versioning — har spec o'zgarishida append-only snapshot yozadi."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Max


@transaction.atomic
def record_template_version(template, spec: dict, note: str, user):
    """Set the template's current spec and append a new version snapshot.

    Returns the created TemplateVersionModel row.
    """
    from core.apps.template.models import TemplateVersionModel

    next_v = (template.versions.aggregate(m=Max("version"))["m"] or 0) + 1
    template.spec = spec
    template.version = next_v
    template.save(update_fields=["spec", "version", "updated_at"])
    return TemplateVersionModel.objects.create(
        template=template,
        version=next_v,
        spec=spec,
        note=note or "",
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
