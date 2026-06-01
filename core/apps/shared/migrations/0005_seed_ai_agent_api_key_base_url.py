"""Data migration: seed ai_agent.base_url and ai_agent.api_key config entries (idempotent)."""

from django.db import migrations

NEW_CONFIGS = [
    {
        "key": "ai_agent.base_url",
        "value": "",
        "label": "AI Agent Base URL",
        "group": "ai_agent",
        "is_public": True,
        "description": "Base URL for the AI agent API endpoint (e.g. https://api.openai.com/v1).",
    },
    {
        "key": "ai_agent.api_key",
        "value": "",
        "label": "AI Agent API Key",
        "group": "ai_agent",
        "is_public": False,
        "description": "Secret API key for the AI agent. Not served on the public endpoint.",
    },
]


def seed_configs(apps, schema_editor):
    Config = apps.get_model("shared", "Config")
    for entry in NEW_CONFIGS:
        Config.objects.get_or_create(
            key=entry["key"],
            defaults={
                "value": entry["value"],
                "label": entry["label"],
                "group": entry["group"],
                "is_public": entry["is_public"],
                "description": entry["description"],
            },
        )


def unseed_configs(apps, schema_editor):
    Config = apps.get_model("shared", "Config")
    keys = [e["key"] for e in NEW_CONFIGS]
    Config.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shared", "0004_seed_ai_agent_config"),
    ]

    operations = [
        migrations.RunPython(seed_configs, reverse_code=unseed_configs),
    ]
