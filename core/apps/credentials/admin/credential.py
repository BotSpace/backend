from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.credentials.models import Credential


@admin.register(Credential)
class CredentialAdmin(ModelAdmin):
    list_display = ["name", "project", "type", "owner", "deleted_at", "created_at"]
    list_filter = ["type", "deleted_at"]
    search_fields = ["name", "project__id"]
    readonly_fields = ["data_encrypted", "created_at", "updated_at"]
    raw_id_fields = ["project", "owner", "type"]
