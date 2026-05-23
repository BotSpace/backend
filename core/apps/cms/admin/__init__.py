from django.contrib import admin

from core.apps.cms.models import AuditLog, Collection, Field, Webhook


class FieldInline(admin.TabularInline):
    model = Field
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "project", "schema_version", "system", "deleted_at")
    list_filter = ("system",)
    search_fields = ("name", "label")
    inlines = [FieldInline]


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ("id", "collection", "name", "kind", "required", "index")
    list_filter = ("kind", "index", "required")
    search_fields = ("name", "label")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "collection", "action", "document_id", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("document_id",)
    readonly_fields = ("created_at",)


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("id", "collection", "event", "url", "active", "last_status", "last_fired_at")
    list_filter = ("event", "active")
    search_fields = ("url",)
