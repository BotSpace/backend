"""
Admin panel register
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth import models as db_models
from django_core.models import SmsConfirm
from unfold.admin import ModelAdmin

from ..admin import user
from ..models import LoginLog
from .user import SmsConfirmAdmin

admin.site.unregister(db_models.Group)
admin.site.register(db_models.Group, user.GroupAdmin)
admin.site.register(db_models.Permission, user.PermissionAdmin)

admin.site.register(get_user_model(), user.CustomUserAdmin)
admin.site.register(SmsConfirm, SmsConfirmAdmin)


@admin.register(LoginLog)
class LoginLogAdmin(ModelAdmin):
    list_display = ("user", "method", "created_at")
    list_filter = ("method",)
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    readonly_fields = ("user", "method", "created_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
