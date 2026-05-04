from django.db import migrations, models


def convert_empty_phone_to_null(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(phone="").update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_user_phone"),
    ]

    operations = [
        migrations.RunPython(convert_empty_phone_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, default=None, max_length=255, null=True, unique=True),
        ),
    ]
