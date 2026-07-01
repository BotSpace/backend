"""Data migration: mavjud TemplateModel'lar uchun spec to'ldirish."""
from django.db import migrations


def forward(apps, schema_editor):
    TemplateModel = apps.get_model("template", "TemplateModel")
    # Avval build_spec_from_project import qilamiz — lekin migration'da
    # model state farq qilgani uchun service'ni to'g'ridan-to'g'ri chaqirib bo'lmaydi.
    # Shu sababli faqat required_envs → spec.envs migratsiyasini shu yerda qilamiz.
    # Collections/credentials/modules uchun TemplateModel.project hali bog'liq bo'lsa,
    # admin panel'dagi "resync" action'i to'liq spec'ni qurishga ishlatiladi.
    for tmpl in TemplateModel.objects.filter(spec={}).iterator():
        spec = dict(tmpl.spec) if tmpl.spec else {}
        if not spec.get("envs"):
            required_envs = tmpl.required_envs or []
            spec["envs"] = [
                {"key": item.get("key", ""), "required": True, "description": item.get("description", "")}
                for item in required_envs
                if isinstance(item, dict) and item.get("key")
            ]
        if not spec.get("flow") and tmpl.project_id:
            try:
                # apps.get_model bilan flow'ni olishga urinib ko'ramiz
                ProjectModel = apps.get_model("api", "ProjectModel")
                proj = ProjectModel.objects.filter(id=tmpl.project_id).first()
                if proj and proj.flow:
                    spec["flow"] = proj.flow
            except Exception:
                pass
        if not spec.get("collections"):
            spec["collections"] = []
        if not spec.get("credentials"):
            spec["credentials"] = []
        if not spec.get("modules"):
            spec["modules"] = []
        tmpl.spec = spec
        tmpl.save(update_fields=["spec"])


def backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("template", "0019_template_spec"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
