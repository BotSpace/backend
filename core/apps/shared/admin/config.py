from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.shared.models import Config


@admin.register(Config)
class ConfigAdmin(ModelAdmin):
    list_display = ["key", "group", "label", "is_public", "updated_at"]
    list_filter = ["group", "is_public"]
    search_fields = ["key", "label", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["group", "key"]
    list_per_page = 50
    fieldsets = [
        (
            None,
            {
                "fields": ["key", "value", "label", "group", "is_public", "description"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]
