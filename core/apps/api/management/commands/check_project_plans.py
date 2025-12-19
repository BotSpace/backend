# type: ignore
"""
Management command to check and fix projects plan assignments
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from rich.console import Console
from rich.table import Table

from core.apps.api.models import ProjectModel, PlanModel, ProjectPlanModel
from core.apps.api.enums.plan import PlanType, PlanStatus

console = Console()


class Command(BaseCommand):
    help = "Check projects plan status and fix issues"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix issues automatically',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        
        console.print("\n[cyan]Checking projects plan status...[/cyan]\n")
        
        # Statistics
        total_projects = ProjectModel.objects.count()
        projects_with_plan = ProjectPlanModel.objects.count()
        projects_without_plan = total_projects - projects_with_plan
        
        # Plan distribution
        plan_distribution = {}
        for plan in PlanModel.objects.all():
            count = ProjectPlanModel.objects.filter(plan=plan).count()
            plan_distribution[plan.get_name_display()] = count
        
        # Status distribution
        status_distribution = {}
        for status_choice in PlanStatus.choices:
            status = status_choice[0]
            count = ProjectPlanModel.objects.filter(status=status).count()
            if count > 0:
                status_distribution[status_choice[1]] = count
        
        # Display statistics
        console.print("[bold cyan]Overview:[/bold cyan]")
        console.print(f"  Total projects: {total_projects}")
        console.print(f"  With plans: [green]{projects_with_plan}[/green]")
        console.print(f"  Without plans: [{'red' if projects_without_plan > 0 else 'green'}]{projects_without_plan}[/{'red' if projects_without_plan > 0 else 'green'}]")
        console.print()
        
        # Plan distribution table
        if plan_distribution:
            plan_table = Table(title="Plan Distribution")
            plan_table.add_column("Plan", style="cyan")
            plan_table.add_column("Projects", style="white", justify="right")
            plan_table.add_column("Percentage", style="yellow", justify="right")
            
            for plan_name, count in plan_distribution.items():
                percentage = (count / projects_with_plan * 100) if projects_with_plan > 0 else 0
                plan_table.add_row(
                    plan_name,
                    str(count),
                    f"{percentage:.1f}%"
                )
            
            console.print(plan_table)
            console.print()
        
        # Status distribution table
        if status_distribution:
            status_table = Table(title="Status Distribution")
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Projects", style="white", justify="right")
            
            for status_name, count in status_distribution.items():
                status_table.add_row(status_name, str(count))
            
            console.print(status_table)
            console.print()
        
        # Find issues
        issues = []
        
        # Issue 1: Projects without plans
        if projects_without_plan > 0:
            issues.append({
                'type': 'missing_plan',
                'count': projects_without_plan,
                'description': f'{projects_without_plan} projects without plan',
                'severity': 'high'
            })
        
        # Issue 2: Projects in grace period
        grace_period_count = ProjectPlanModel.objects.filter(
            status=PlanStatus.GRACE_PERIOD
        ).count()
        if grace_period_count > 0:
            issues.append({
                'type': 'grace_period',
                'count': grace_period_count,
                'description': f'{grace_period_count} projects in grace period',
                'severity': 'warning'
            })
        
        # Issue 3: Suspended projects
        suspended_count = ProjectPlanModel.objects.filter(
            status=PlanStatus.SUSPENDED
        ).count()
        if suspended_count > 0:
            issues.append({
                'type': 'suspended',
                'count': suspended_count,
                'description': f'{suspended_count} projects suspended',
                'severity': 'high'
            })
        
        # Display issues
        if issues:
            console.print("[bold yellow]Issues Found:[/bold yellow]")
            
            issues_table = Table()
            issues_table.add_column("Type", style="cyan")
            issues_table.add_column("Count", style="white", justify="right")
            issues_table.add_column("Severity", style="yellow")
            issues_table.add_column("Description", style="white")
            
            for issue in issues:
                severity_color = "red" if issue['severity'] == 'high' else "yellow"
                issues_table.add_row(
                    issue['type'],
                    str(issue['count']),
                    f"[{severity_color}]{issue['severity']}[/{severity_color}]",
                    issue['description']
                )
            
            console.print(issues_table)
            console.print()
            
            # Fix issues
            if fix:
                console.print("[cyan]Fixing issues...[/cyan]\n")
                
                # Fix missing plans
                if projects_without_plan > 0:
                    console.print(f"[yellow]Assigning FREE plan to {projects_without_plan} projects...[/yellow]")
                    
                    try:
                        free_plan = PlanModel.objects.get(
                            name=PlanType.FREE,
                            is_active=True
                        )
                        
                        fixed_count = 0
                        with transaction.atomic():
                            for project in ProjectModel.objects.all():
                                try:
                                    project.plan_subscription
                                except ProjectPlanModel.DoesNotExist:
                                    ProjectPlanModel.objects.create(
                                        project=project,
                                        plan=free_plan,
                                        status=PlanStatus.ACTIVE,
                                        current_users=0
                                    )
                                    fixed_count += 1
                        
                        console.print(f"[green]✓ Assigned FREE plan to {fixed_count} projects[/green]\n")
                    
                    except PlanModel.DoesNotExist:
                        console.print("[red]✗ FREE plan not found! Run: python manage.py create_pricing_plans[/red]\n")
                
                console.print("[green]✓ All issues fixed![/green]\n")
            else:
                console.print("[yellow]Run with --fix to automatically fix these issues[/yellow]\n")
        else:
            console.print("[green]✓ No issues found! All projects are properly configured.[/green]\n")
        
        console.print("[bold cyan]Recommendations:[/bold cyan]")
        
        if projects_without_plan > 0:
            console.print("  • Run: [white]python manage.py assign_plans_to_projects[/white]")
        
        if grace_period_count > 0:
            console.print(f"  • {grace_period_count} projects need plan upgrade")
        
        if suspended_count > 0:
            console.print(f"  • {suspended_count} projects are suspended and need attention")
        
        console.print()
