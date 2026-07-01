"""Migration: TemplateModel.spec (JSONField) qo'shish + project FK CASCADE → SET_NULL."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
        ("template", "0018_required_envs"),
    ]

    operations = [
        # 1. spec field qo'shish
        migrations.AddField(
            model_name="templatemodel",
            name="spec",
            field=models.JSONField(default=dict, blank=True, verbose_name="spec"),
        ),
        # 2. project FK: CASCADE → SET_NULL
        migrations.AlterField(
            model_name="templatemodel",
            name="project",
            field=models.ForeignKey(
                to="api.ProjectModel",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                verbose_name="project",
            ),
        ),
    ]
