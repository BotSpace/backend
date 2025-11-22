from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.api.models.message import MessageModel


@admin.register(MessageModel)
class MessageAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
