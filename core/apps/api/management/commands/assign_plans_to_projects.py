# type: ignore
"""
Management command to assign FREE plan to projects without a plan
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from rich.console import Console
from rich.table import Table

from core.apps.api.models import ProjectModel, PlanModel, ProjectPlanModel
from core.apps.api.enums.plan import PlanType, PlanStatus

console = Console()


class Command(BaseCommand):
    help = "Assign FREE plan to all projects without a plan"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--plan',
            type=str,
            default='free',
            choices=['free', 'start', 'pro', 'enterprise'],
            help='Which plan to assign (default: free)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        plan_name = options['plan']
        
        console.print("\n[cyan]Checking projects without plans...[/cyan]\n")
        
        # Get the plan to assign
        try:
            plan = PlanModel.objects.get(
                name=plan_name.lower(),
                is_active=True
            )
        except PlanModel.DoesNotExist:
            console.print(f"[red]Error: {plan_name.upper()} plan not found or inactive![/red]")
            console.print("[yellow]Please run: python manage.py create_pricing_plans[/yellow]\n")
            return
        
        # Find projects without plans
        projects_without_plan = []
        
        for project in ProjectModel.objects.select_related('owner').all():
            try:
                # Try to get existing plan
                project.plan_subscription
            except ProjectPlanModel.DoesNotExist:
                # No plan assigned
                projects_without_plan.append(project)
        
        if not projects_without_plan:
            console.print("[green]✓ All projects already have plans assigned![/green]\n")
            return
        
        # Display projects that will be updated
        table = Table(title=f"Projects without plans ({len(projects_without_plan)})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Owner", style="yellow")
        table.add_column("Created", style="blue")
        
        for project in projects_without_plan[:20]:  # Show first 20
            table.add_row(
                str(project.id),
                project.name[:40] + ('...' if len(project.name) > 40 else ''),
                str(project.owner)[:30],
                project.created_at.strftime('%Y-%m-%d %H:%M')
            )
        
        if len(projects_without_plan) > 20:
            console.print(table)
            console.print(f"[dim]... and {len(projects_without_plan) - 20} more[/dim]\n")
        else:
            console.print(table)
            console.print()
        
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would assign {plan.get_name_display()} plan to {len(projects_without_plan)} projects[/yellow]\n")
            return
        
        # Confirm
        console.print(f"[bold yellow]About to assign {plan.get_name_display()} plan to {len(projects_without_plan)} projects.[/bold yellow]")
        confirm = input("Continue? [y/N]: ")
        
        if confirm.lower() != 'y':
            console.print("\n[red]Cancelled.[/red]\n")
            return
        
        # Assign plans
        assigned_count = 0
        failed_count = 0
        
        console.print(f"\n[cyan]Assigning {plan.get_name_display()} plan...[/cyan]\n")
        
        with transaction.atomic():
            for project in projects_without_plan:
                try:
                    ProjectPlanModel.objects.create(
                        project=project,
                        plan=plan,
                        status=PlanStatus.ACTIVE,
                        current_users=0
                    )
                    assigned_count += 1
                    console.print(
                        f"[green]✓[/green] Project #{project.id}: {project.name[:40]}"
                    )
                except Exception as e:
                    failed_count += 1
                    console.print(
                        f"[red]✗[/red] Project #{project.id}: {str(e)[:60]}"
                    )
        
        # Summary
        console.print(f"\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  [green]Assigned:[/green] {assigned_count}")
        if failed_count > 0:
            console.print(f"  [red]Failed:[/red] {failed_count}")
        console.print(f"  [blue]Plan:[/blue] {plan.get_name_display()}")
        console.print(f"  [blue]Total projects:[/blue] {ProjectModel.objects.count()}")
        console.print(f"  [blue]With plans:[/blue] {ProjectPlanModel.objects.count()}")
        console.print("\n[green]✓ Done![/green]\n")
