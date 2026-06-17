"""Data migration: seed 4 built-in CredentialTypes.

Idempotent — uses update_or_create on key so re-running is safe.
"""
from __future__ import annotations

from django.db import migrations

BUILTIN_TYPES = [
    {
        "key": "api_key",
        "label": "API Key / Token",
        "icon": "key",
        "mode": "apikey",
        "system": True,
        "fields": [
            {
                "name": "token",
                "label": "API Key / Token",
                "type": "password",
                "secret": True,
                "required": True,
            },
            {
                "name": "param_name",
                "label": "Header / query name",
                "type": "text",
                "required": True,
                "default": "X-API-Key",
            },
            {
                "name": "placement",
                "label": "Joylashuv",
                "type": "select",
                "required": True,
                "default": "header",
                "options": [
                    {"value": "header", "label": "Header"},
                    {"value": "query", "label": "Query param"},
                ],
            },
        ],
    },
    {
        "key": "bearer",
        "label": "Bearer Token",
        "icon": "shield",
        "mode": "bearer",
        "system": True,
        "fields": [
            {
                "name": "token",
                "label": "Token",
                "type": "password",
                "secret": True,
                "required": True,
            }
        ],
    },
    {
        "key": "header_auth",
        "label": "Header Auth",
        "icon": "list",
        "mode": "header",
        "system": True,
        "fields": [
            {
                "name": "header_name",
                "label": "Header nomi",
                "type": "text",
                "required": True,
                "default": "Authorization",
            },
            {
                "name": "header_value",
                "label": "Header qiymati",
                "type": "password",
                "secret": True,
                "required": True,
            },
        ],
    },
    {
        "key": "basic_auth",
        "label": "Basic Auth",
        "icon": "user",
        "mode": "basic",
        "system": True,
        "fields": [
            {
                "name": "username",
                "label": "Username",
                "type": "text",
                "required": True,
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "secret": True,
                "required": True,
            },
        ],
    },
]


def seed_builtin_types(apps, schema_editor):
    CredentialType = apps.get_model("credentials", "CredentialType")
    for entry in BUILTIN_TYPES:
        key = entry.pop("key")
        CredentialType.objects.update_or_create(
            key=key,
            defaults={**entry, "owner": None},
        )
        entry["key"] = key  # restore for potential re-runs


def reverse_seed(apps, schema_editor):
    CredentialType = apps.get_model("credentials", "CredentialType")
    keys = [t["key"] for t in BUILTIN_TYPES]
    CredentialType.objects.filter(key__in=keys, system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("credentials", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_builtin_types, reverse_seed),
    ]
