from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.template.models import TemplateModel


@admin.register(TemplateModel)
class TemplateAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
