"""Data migration: seed default AI agent config entries (idempotent get_or_create)."""

from django.db import migrations

AI_AGENT_CONFIGS = [
    {
        "key": "ai_agent.provider",
        "value": "bedrock",
        "label": "AI Agent Provider",
        "group": "ai_agent",
        "is_public": True,
        "description": "LLM provider used by the AI agent (e.g. bedrock, openai).",
    },
    {
        "key": "ai_agent.model",
        "value": "qwen.qwen3-coder-480b-a35b-v1:0",
        "label": "AI Agent Model",
        "group": "ai_agent",
        "is_public": True,
        "description": "Model identifier passed to the provider.",
    },
    {
        "key": "ai_agent.region",
        "value": "us-west-2",
        "label": "AI Agent Region",
        "group": "ai_agent",
        "is_public": True,
        "description": "AWS region for Bedrock API calls.",
    },
]


def seed_ai_agent_configs(apps, schema_editor):
    Config = apps.get_model("shared", "Config")
    for entry in AI_AGENT_CONFIGS:
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


def unseed_ai_agent_configs(apps, schema_editor):
    Config = apps.get_model("shared", "Config")
    keys = [e["key"] for e in AI_AGENT_CONFIGS]
    Config.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shared", "0003_config"),
    ]

    operations = [
        migrations.RunPython(seed_ai_agent_configs, reverse_code=unseed_ai_agent_configs),
    ]
