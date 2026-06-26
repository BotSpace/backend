# Generated migration — ADD COLUMN only (safe on botspace-owned table)
from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0062_plan_add_max_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="planmodel",
            name="cached_token_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.10"),
                help_text="Keshlangan tokenlarning kvotaga hisoblanish ulushi (0.10 = 10%, 1.00 = to'liq, 0.00 = bepul)",
                max_digits=4,
                verbose_name="Keshlangan token koeffitsienti",
            ),
        ),
    ]
