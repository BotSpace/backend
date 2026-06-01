"""Data migration: seed ai_agent.aws_access_key_id and ai_agent.aws_secret_access_key config entries (idempotent)."""

from django.db import migrations

NEW_CONFIGS = [
    {
        "key": "ai_agent.aws_access_key_id",
        "value": "",
        "label": "AI Agent AWS Access Key ID",
        "group": "ai_agent",
        "is_public": False,
        "description": "AWS Bedrock access key ID. Not served on the public endpoint.",
    },
    {
        "key": "ai_agent.aws_secret_access_key",
        "value": "",
        "label": "AI Agent AWS Secret Access Key",
        "group": "ai_agent",
        "is_public": False,
        "description": "AWS Bedrock secret access key. Not served on the public endpoint.",
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
        ("shared", "0005_seed_ai_agent_api_key_base_url"),
    ]

    operations = [
        migrations.RunPython(seed_configs, reverse_code=unseed_configs),
    ]
