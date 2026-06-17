from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.credentials.models import CredentialType


@admin.register(CredentialType)
class CredentialTypeAdmin(ModelAdmin):
    list_display = ["key", "label", "mode", "system", "owner", "created_at"]
    list_filter = ["mode", "system"]
    search_fields = ["key", "label"]
    readonly_fields = ["created_at", "updated_at"]

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.system:
            ro += ["key", "mode", "fields"]
        return ro
