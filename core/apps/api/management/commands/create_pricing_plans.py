# type: ignore
"""
Management command to create initial pricing plans
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from rich.console import Console

from core.apps.api.models import PlanModel
from core.apps.api.enums.plan import PlanType

console = Console()


class Command(BaseCommand):
    help = "Create initial pricing plans"

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing plans',
        )

    def handle(self, *args, **options):
        update = options['update']
        
        console.print("\n[cyan]Creating pricing plans...[/cyan]\n")
        
        plans_data = [
            {
                'name': PlanType.FREE,
                'price': Decimal('0.00'),
                'max_users': 100,
                'powered_by_botmother': True,
                'custom_domain': False,
                'priority_support': False,
                'description': 'Bepul tarif - 100 tagacha foydalanuvchi. "Powered by BotMother" brending bilan.',
                'order': 1,
            },
            {
                'name': PlanType.START,
                'price': Decimal('2.00'),
                'max_users': 5000,
                'powered_by_botmother': False,
                'custom_domain': False,
                'priority_support': False,
                'description': 'Start tarifi - 5,000 tagacha foydalanuvchi. Brending yo\'q.',
                'order': 2,
            },
            {
                'name': PlanType.PRO,
                'price': Decimal('10.00'),
                'max_users': 100000,
                'powered_by_botmother': False,
                'custom_domain': True,
                'priority_support': True,
                'description': 'Pro tarifi - 100,000 tagacha foydalanuvchi. Custom domain va priority support.',
                'order': 3,
            },
            {
                'name': PlanType.ENTERPRISE,
                'price': Decimal('0.00'),  # Custom pricing
                'max_users': 999999999,  # Unlimited
                'powered_by_botmother': False,
                'custom_domain': True,
                'priority_support': True,
                'description': 'Enterprise tarifi - Cheksiz foydalanuvchi. Narx kelishiladi.',
                'order': 4,
            },
        ]
        
        created = 0
        updated = 0
        
        for plan_data in plans_data:
            plan, created_flag = PlanModel.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            
            if created_flag:
                console.print(f"[green]✓ Created:[/green] {plan.get_name_display()} - ${plan.price}/month")
                created += 1
            elif update:
                for key, value in plan_data.items():
                    if key != 'name':
                        setattr(plan, key, value)
                plan.save()
                console.print(f"[yellow]↻ Updated:[/yellow] {plan.get_name_display()} - ${plan.price}/month")
                updated += 1
            else:
                console.print(f"[blue]- Exists:[/blue] {plan.get_name_display()} - ${plan.price}/month")
        
        console.print(f"\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  Created: {created}")
        console.print(f"  Updated: {updated}")
        console.print(f"  Total: {PlanModel.objects.count()}")
        console.print("\n[green]✓ Done![/green]\n")
