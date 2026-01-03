# type: ignore
"""
Management command to recreate all releases

This command redeploys all release instances using deploy_service.
"""
from django.core.management.base import BaseCommand
from rich.console import Console

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import RelaseModel
from core.apps.api.services.docker_service import deploy_service, remove_service
from core.apps.api.services.enviroment import project_enviroment
from core.apps.api.signals.project import invalidate_webhook_cache

console = Console()


class Command(BaseCommand):
    help = "Recreate all releases by redeploying them using deploy_service"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            type=int,
            help="Recreate releases only for specific project ID",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        project_id = options.get("project")
        dry_run = options.get("dry_run", False)

        console.print("\n[cyan]Recreating releases...[/cyan]\n")

        # Get all releases or filter by project
        queryset = RelaseModel.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            console.print(f"[yellow]Filtering by project ID: {project_id}[/yellow]\n")

        releases = queryset.select_related("project").order_by("project_id", "-version")

        if not releases.exists():
            console.print("[yellow]No releases found.[/yellow]\n")
            return

        total_count = releases.count()
        console.print(f"[bold]Found {total_count} release(s) to recreate[/bold]\n")

        if dry_run:
            console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")

        recreated = 0
        failed = 0
        skipped = 0

        # Group releases by project to only recreate the latest one per project
        processed_projects = set()

        for release in releases:
            # Skip if we already processed this project (only recreate latest release per project)
            if release.project_id in processed_projects:
                skipped += 1
                console.print(
                    f"[dim]- Skipped:[/dim] Release v{release.version} "
                    f"for project '{release.project.name}' (ID: {release.project_id}) - "
                    f"newer release already processed"
                )
                continue

            processed_projects.add(release.project_id)

            try:
                console.print(
                    f"[cyan]Processing:[/cyan] Release v{release.version} "
                    f"for project '{release.project.name}' (ID: {release.project_id})"
                )

                if dry_run:
                    console.print(
                        f"  [dim]Would redeploy: project={release.project_id}, "
                        f"version={release.version}, status={release.status}[/dim]"
                    )
                    recreated += 1
                    continue

                # Remove old service if it exists
                if release.service_id:
                    console.print(f"  [yellow]Removing old service: {release.service_id}[/yellow]")
                    remove_service(release.service_id)
                    release.status = ContainerStatusEnum.STOPPING.value
                    release.save(update_fields=["status"])

                # Deploy new service
                console.print("  [cyan]Deploying new service...[/cyan]")
                service = deploy_service(
                    release.project,
                    "release",
                    release.flow,
                    "%s_%s" % (release.project.pk, release.version),
                    [*list(project_enviroment(release.project.id)), "IS_RELEASE=true"],
                    webhook_uuid=str(release.project.release_webhook_uuid),
                )

                # Update release with new service info
                release.service_id = service.metadata.name
                release.status = ContainerStatusEnum.INIT.value
                release.save(update_fields=["service_id", "status"])

                # Invalidate webhook cache
                invalidate_webhook_cache(release.project, "release")

                console.print(
                    f"  [green]✓ Recreated:[/green] service_id={service.metadata.name}, " f"status={release.status}"
                )
                recreated += 1

            except Exception as e:
                failed += 1
                console.print(
                    f"  [red]✗ Failed:[/red] Release v{release.version} "
                    f"for project '{release.project.name}' (ID: {release.project_id})"
                )
                console.print(f"  [red]Error: {str(e)}[/red]")
                self.stderr.write(self.style.ERROR(f"Error recreating release {release.id}: {str(e)}"))

        # Print summary
        console.print("\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  Total releases: {total_count}")
        console.print(f"  Recreated: {recreated}")
        console.print(f"  Skipped: {skipped}")
        console.print(f"  Failed: {failed}")

        if dry_run:
            console.print("\n[yellow]DRY RUN - No actual changes were made[/yellow]")
        else:
            console.print("\n[green]✓ Done![/green]\n")
