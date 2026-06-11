from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.payment.models import HistoryModel


@admin.register(HistoryModel)
class HistoryAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "type_display",
        "amount",
        "comment",
        "created_at",
    )
    list_filter = ("type",)
    search_fields = ("user__phone", "comment")

    @admin.display(description="Tur", ordering="type")
    def type_display(self, obj):
        # Kirim / Chiqim (choices label)
        return obj.get_type_display()
