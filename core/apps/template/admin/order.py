from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.template.models import TemplateOrderModel


@admin.register(TemplateOrderModel)
class TemplateOrderAdmin(ModelAdmin):
    list_display = (
        "id",
        "user__first_name",
        "template__name",
        "status",
        "payment_status",
    )
