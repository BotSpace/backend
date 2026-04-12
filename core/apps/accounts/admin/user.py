from django import forms
from django.contrib.auth import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


class CustomUserChangeForm(UserChangeForm):
    """Phone fieldi bo'sh bo'lishi mumkin bo'lgan foydalanuvchilar uchun."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "phone" in self.fields:
            self.fields["phone"].required = False


class CustomUserAdmin(admin.UserAdmin, ModelAdmin):
    change_password_form = AdminPasswordChangeForm
    add_form = UserCreationForm
    form = CustomUserChangeForm
    list_display = (
        "first_name",
        "last_name",
        "phone",
        "role",
        "balance",
        "template_balance",
    )
    search_fields = ("phone", "first_name", "last_name", "email")
    ordering = ("phone",)
    filter_horizontal = ()
    readonly_fields = ("last_login", "date_joined")
    autocomplete_fields = ["groups", "user_permissions"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "password1", "password2"),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "username", "balance", "template_balance")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "role",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


class PermissionAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class GroupAdmin(ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    autocomplete_fields = ("permissions",)


class SmsConfirmAdmin(ModelAdmin):
    list_display = ["phone", "code", "resend_count", "try_count"]
    search_fields = ["phone", "code"]
