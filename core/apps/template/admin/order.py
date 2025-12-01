from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from core.apps.template.models import TemplateOrderModel


@admin.register(TemplateOrderModel)
class TemplateOrderAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_name",
        "template_name",
        "status",
        "payment_status",
    )
    
    @display(description="User")
    def user_name(self, obj):
        return obj.user.first_name if obj.user else "-"
    
    @display(description="Template")
    def template_name(self, obj):
        return obj.template.name if obj.template else "-"
