from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0048_projectplan_tokens"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="ProjectPlanModel"),
            ],
        ),
    ]
