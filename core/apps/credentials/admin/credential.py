from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.credentials.models import Credential


@admin.register(Credential)
class CredentialAdmin(ModelAdmin):
    list_display = ["name", "owner", "type_key", "deleted_at", "created_at"]
    list_filter = ["type_key", "deleted_at"]
    search_fields = ["name", "owner__username", "owner__id"]
    readonly_fields = ["data_encrypted", "created_at", "updated_at"]
    raw_id_fields = ["owner"]
