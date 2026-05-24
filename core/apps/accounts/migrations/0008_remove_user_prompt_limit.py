from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_user_prompt_limit"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="user",
                    name="prompt_limit",
                ),
            ],
        ),
    ]
