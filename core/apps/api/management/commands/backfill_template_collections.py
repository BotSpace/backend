"""Retro-fix an already-created bot whose cmsv2 collections / catalog data were
never copied from its template (the `create_from_template` bug).

Usage:
    python manage.py backfill_template_collections --project 1285 --from-template 7
    python manage.py backfill_template_collections --project 1285          # auto-detect template
    python manage.py backfill_template_collections --project 1285 --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.apps.api.models.project import ProjectModel
from core.apps.api.services.project import collection_is_catalog, copy_cms_collections
from core.apps.template.models.order import TemplateOrderModel
from core.apps.template.models.template import TemplateModel


class Command(BaseCommand):
    help = "Backfill cmsv2 collections + catalog data for a bot created from a template."

    def add_arguments(self, parser):
        parser.add_argument("--project", type=int, required=True, help="Target project (bot) id.")
        parser.add_argument(
            "--from-template",
            type=int,
            default=None,
            help="Template id to copy from. If omitted, auto-detected via the owner's paid TemplateOrder.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be copied; make no changes.",
        )

    def handle(self, *args, **options):
        project_id = options["project"]
        template_id = options["from_template"]
        dry_run = options["dry_run"]

        try:
            project = ProjectModel.objects.get(pk=project_id)
        except ProjectModel.DoesNotExist:
            raise CommandError(f"Project {project_id} not found.")

        template = self._resolve_template(template_id, project)
        source_project = template.project
        if not source_project:
            raise CommandError(f"Template {template.pk} has no source project.")

        self.stdout.write(
            f"Backfilling project {project.pk} ({project.name!r}) "
            f"from template {template.pk} (source project {source_project.pk})."
        )

        if dry_run:
            self._dry_run(source_project, project)
            return

        copy_cms_collections(source_project, project, flow=project.flow)
        self.stdout.write(self.style.SUCCESS("Done."))

    def _resolve_template(self, template_id, project):
        if template_id is not None:
            try:
                return TemplateModel.objects.get(pk=template_id)
            except TemplateModel.DoesNotExist:
                raise CommandError(f"Template {template_id} not found.")

        order = (
            TemplateOrderModel.objects.filter(user=project.owner, payment_status=True, template__isnull=False)
            .order_by("-id")
            .first()
        )
        if order is None or order.template is None:
            raise CommandError(
                "Could not auto-detect template. Pass --from-template <id> explicitly."
            )
        self.stdout.write(
            self.style.WARNING(
                f"Auto-detected template {order.template.pk} via TemplateOrder {order.pk}."
            )
        )
        return order.template

    def _dry_run(self, source_project, project):
        from core.apps.cms.services.mongo import get_mongo_client

        client = get_mongo_client()
        try:
            names = client.get_project_database(source_project.id).list_collection_names()
        except Exception as exc:  # pragma: no cover - defensive
            raise CommandError(f"Failed to list source collections: {exc}")

        flow = project.flow
        for name in sorted(n for n in names if isinstance(n, str) and not n.startswith("system.")):
            is_catalog = collection_is_catalog(flow, name)
            action = "schema + DATA (catalog)" if is_catalog else "schema only"
            self.stdout.write(f"  - {name}: {action}")
        self.stdout.write(self.style.WARNING("Dry run — no changes made."))
