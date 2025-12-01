# type: ignore
"""
Management command to create MongoDB users for existing projects
"""
from django.core.management.base import BaseCommand
from core.apps.api.models import ProjectModel
from core.apps.cms.services.mongo import MongoDBClient
from rich.console import Console
from rich.progress import track

console = Console()


class Command(BaseCommand):
    help = "Create MongoDB users for all existing projects"

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

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        recreate = options.get("recreate")

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

        mongo_client = MongoDBClient()
        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            for project in track(list(projects), description="MongoDB userlar yaratilmoqda..."):
                try:
                    # Check if user already exists
                    username = f"project_{project.id}_user"
                    admin_db = mongo_client.admin_client.admin
                    existing_users = admin_db.command("usersInfo", username)
                    
                    user_exists = len(existing_users.get("users", [])) > 0
                    
                    if user_exists and not recreate:
                        console.print(
                            f"[yellow]Skip: Project {project.id} ({project.name}) - user allaqachon mavjud[/yellow]"
                        )
                        continue
                    
                    # Create or update user
                    credentials = mongo_client.create_project_user(project.id)
                    
                    if user_exists:
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
                        console.print(f"  Password: {credentials['password']}")
                        created_count += 1

                except Exception as e:
                    error_count += 1
                    console.print(
                        f"[red]✗ Error: Project {project.id} ({project.name}) - {e}[/red]"
                    )

        finally:
            mongo_client.close()

        # Summary
        console.print("\n[bold cyan]Natija:[/bold cyan]")
        console.print(f"  ✓ Yaratildi: {created_count}")
        console.print(f"  ↻ Yangilandi: {updated_count}")
        console.print(f"  ✗ Xatolar: {error_count}")
        
        if created_count + updated_count > 0:
            console.print("\n[green]MongoDB userlar muvaffaqiyatli yaratildi![/green]")
            console.print("[yellow]Eslatma: Parollar faqat yaratilganda ko'rsatiladi. Ularni xavfsiz saqlang![/yellow]")
