# type: ignore
"""
Management command to create MongoDB credentials for existing projects.
The credentials are saved to ProjectModel and reused for all services.
"""
from django.core.management.base import BaseCommand
from core.apps.api.models import ProjectModel
from core.apps.cms.services.mongo import MongoDBClient
from rich.console import Console
from rich.progress import track

console = Console()


class Command(BaseCommand):
    help = "Create MongoDB credentials for all existing projects and save them to ProjectModel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Create user only for specific project ID",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Recreate existing users (updates password)",
        )
        parser.add_argument(
            "--show-passwords",
            action="store_true",
            help="Print generated passwords to stdout (DANGEROUS — disabled by default)",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        recreate = options.get("recreate")
        show_passwords = options.get("show_passwords")

        # Get projects
        if project_id:
            projects = ProjectModel.objects.filter(id=project_id)
            if not projects.exists():
                console.print(f"[red]Project ID {project_id} topilmadi[/red]")
                return
        else:
            projects = ProjectModel.objects.all()

        if not projects.exists():
            console.print("[yellow]Hech qanday project topilmadi[/yellow]")
            return

        console.print(f"\n[cyan]Jami {projects.count()} ta project topildi[/cyan]\n")

        created_count = 0
        updated_count = 0
        error_count = 0

        for project in track(list(projects), description="MongoDB credentials yaratilmoqda..."):
            try:
                # Check if credentials already exist
                has_credentials = bool(
                    project.mongo_username and 
                    project.mongo_password and 
                    project.mongo_database
                )
                
                if has_credentials and not recreate:
                    console.print(
                        f"[yellow]Skip: Project {project.id} ({project.name}) - credentials allaqachon mavjud[/yellow]"
                    )
                    continue
                
                # Get or create credentials (saves to project automatically)
                credentials = project.get_mongo_credentials()
                
                if has_credentials:
                    console.print(
                        f"[green]✓ Updated: Project {project.id} ({project.name})[/green]"
                    )
                    console.print(f"  Username: {credentials['username']}")
                    console.print(f"  Database: {credentials['database']}")
                    updated_count += 1
                else:
                    console.print(
                        f"[green]✓ Created: Project {project.id} ({project.name})[/green]"
                    )
                    console.print(f"  Username: {credentials['username']}")
                    console.print(f"  Database: {credentials['database']}")
                    if show_passwords:
                        console.print(f"  Password: {credentials['password']}")
                    else:
                        console.print("  Password: [hidden — use --show-passwords]")
                    created_count += 1

            except Exception as e:
                error_count += 1
                console.print(
                    f"[red]✗ Error: Project {project.id} ({project.name}) - {e}[/red]"
                )

        # Summary
        console.print("\n[bold cyan]Natija:[/bold cyan]")
        console.print(f"  ✓ Yaratildi: {created_count}")
        console.print(f"  ↻ Yangilandi: {updated_count}")
        console.print(f"  ✗ Xatolar: {error_count}")
        
        if created_count + updated_count > 0:
            console.print("\n[green]MongoDB credentials muvaffaqiyatli yaratildi va saqlandi![/green]")
            console.print("[yellow]Eslatma: Parollar ProjectModel ichida saqlanadi va barcha servicelarda qayta ishlatiladi.[/yellow]")
