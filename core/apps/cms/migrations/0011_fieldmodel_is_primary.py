from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0010_alter_collectionmodel_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldmodel",
            name="is_primary",
            field=models.BooleanField(
                default=False,
                help_text="Marks this field as the primary display field for the collection",
                verbose_name="is primary",
            ),
        ),
    ]
