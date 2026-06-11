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
        
        # Tarif foydalanuvchiga biriktiriladi. Limitlar: bot soni + oylik AI token.
        # (input = umumiy token'ning ~80%, output = ~20%)
        plans_data = [
            {
                'name': PlanType.FREE,
                'price': Decimal('0.00'),
                'max_bots': 1,
                'max_input_tokens': 800_000,
                'max_output_tokens': 200_000,  # jami 1M token/oy
                'description': 'Bepul tarif — 1 ta bot, oyiga 1M AI token.',
                'order': 1,
            },
            {
                'name': PlanType.PRO,
                'price': Decimal('120000.00'),  # so'm/oy (balans so'mda)
                'max_bots': 5,
                'max_input_tokens': 8_000_000,
                'max_output_tokens': 2_000_000,  # jami 10M token/oy
                'description': 'Pro tarifi — 5 ta bot, oyiga 10M AI token.',
                'is_top': True,
                'order': 2,
            },
            {
                'name': PlanType.MAX,
                'price': Decimal('240000.00'),  # so'm/oy (balans so'mda)
                'max_bots': 0,  # cheksiz
                'max_input_tokens': 40_000_000,
                'max_output_tokens': 10_000_000,  # jami 50M token/oy
                'description': 'Max tarifi — cheksiz bot, oyiga 50M AI token.',
                'order': 3,
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
