from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_personalaccesstoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="prompt_limit",
            field=models.PositiveIntegerField(default=5),
        ),
    ]
