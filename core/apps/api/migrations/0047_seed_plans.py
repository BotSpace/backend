from django.db import migrations


PLANS = [
    {
        "name": "free",
        "price": "0.00",
        "max_users": 100,
        "max_bots": 1,
        "max_output_tokens": 200_000,
        "max_input_tokens": 1_000_000,
        "powered_by_botmother": True,
        "custom_domain": False,
        "priority_support": False,
        "is_top": False,
        "is_active": True,
        "order": 0,
        "description": "Boshlang'ich bepul tarif",
        "features": {},
    },
    {
        "name": "pro",
        "price": "10.00",
        "max_users": 1000,
        "max_bots": 10,
        "max_output_tokens": 1_000_000,
        "max_input_tokens": 5_000_000,
        "powered_by_botmother": False,
        "custom_domain": True,
        "priority_support": False,
        "is_top": True,
        "is_active": True,
        "order": 1,
        "description": "Professional tarif",
        "features": {"analytics": True, "custom_domain": True},
    },
    {
        "name": "max",
        "price": "20.00",
        "max_users": 0,
        "max_bots": 0,
        "max_output_tokens": 2_000_000,
        "max_input_tokens": 10_000_000,
        "powered_by_botmother": False,
        "custom_domain": True,
        "priority_support": True,
        "is_top": False,
        "is_active": True,
        "order": 2,
        "description": "Cheksiz imkoniyatli maksimal tarif",
        "features": {"analytics": True, "custom_domain": True, "priority_support": True, "unlimited": True},
    },
]


def seed_plans(apps, schema_editor):
    PlanModel = apps.get_model("api", "PlanModel")
    for plan_data in PLANS:
        PlanModel.objects.update_or_create(
            name=plan_data["name"],
            defaults=plan_data,
        )


def unseed_plans(apps, schema_editor):
    PlanModel = apps.get_model("api", "PlanModel")
    PlanModel.objects.filter(name__in=["free", "pro", "max"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0046_planmodel_new_fields_usersubscription"),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_code=unseed_plans),
    ]
