# type: ignore
"""
Plan admin configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from core.apps.api.models import PlanModel
from core.apps.api.models.plan import UserSubscription


@admin.register(PlanModel)
class PlanAdmin(ModelAdmin):
    """Tarif rejasi admin"""

    list_display = [
        "name_display",
        "price_display",
        "max_users",
        "features_display",
        "is_active",
        "order",
        "subscription_count",
        "is_top",
    ]

    list_filter = ["is_active", "powered_by_botmother"]

    search_fields = ["name", "description"]

    ordering = ["order"]

    fieldsets = (
        (_("Asosiy"), {"fields": ("name", "price", "is_top", "description", "is_active", "order")}),
        (_("Limitlar"), {"fields": ("max_users", "max_bots", "max_input_tokens", "max_output_tokens")}),
        (_("Xususiyatlar"), {"fields": ("powered_by_botmother", "custom_domain", "priority_support")}),
    )

    @display(description=_("Tarif"))
    def name_display(self, obj):
        return obj.get_name_display()

    @display(description=_("Narx"))
    def price_display(self, obj):
        if obj.price == 0:
            return format_html('<span style="color: green; font-weight: bold;">BEPUL</span>')
        return format_html('<span style="font-weight: 500;">${}/oy</span>', obj.price)

    @display(description=_("Xususiyatlar"))
    def features_display(self, obj):
        features = []
        if not obj.powered_by_botmother:
            features.append("✓ No branding")
        if obj.custom_domain:
            features.append("✓ Custom domain")
        if obj.priority_support:
            features.append("✓ Priority support")
        return ", ".join(features) if features else "-"

    @display(description=_("Obunalar"))
    def subscription_count(self, obj):
        count = obj.user_subscriptions.count()
        return format_html(
            '<a href="/admin/api/usersubscription/?plan__id__exact={}" style="font-weight: 600;">{}</a>', obj.id, count
        )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(ModelAdmin):
    """Foydalanuvchi obunasi admin"""

    list_display = [
        "user_display",
        "plan_display",
        "status_display",
        "tokens_output_display",
        "bots_count",
        "started_at",
        "expires_at",
    ]
    list_filter = ["status", "plan__name"]
    search_fields = ["user__phone", "user__email", "user__username"]
    date_hierarchy = "started_at"
    readonly_fields = [
        "tokens_used_input",
        "tokens_used_output",
        "bots_count",
        "token_reset_at",
        "started_at",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (_("Foydalanuvchi"), {"fields": ("user", "plan", "status")}),
        (_("Token statistikasi"), {"fields": ("tokens_used_input", "tokens_used_output", "token_reset_at")}),
        (_("Botlar"), {"fields": ("bots_count",)}),
        (_("Sanalar"), {"fields": ("started_at", "expires_at", "created_at", "updated_at")}),
    )

    @display(description=_("Foydalanuvchi"))
    def user_display(self, obj):
        return str(obj.user)

    @display(description=_("Tarif"))
    def plan_display(self, obj):
        return obj.plan.get_name_display()

    @display(description=_("Holat"), ordering="status")
    def status_display(self, obj):
        colors = {"active": "green", "grace_period": "orange", "suspended": "red", "cancelled": "gray"}
        color = colors.get(obj.status, "black")
        return format_html('<span style="color: {}; font-weight: 600;">{}</span>', color, obj.get_status_display())

    @display(description=_("Output tokenlar"))
    def tokens_output_display(self, obj):
        limit = obj.plan.max_output_tokens
        used = obj.tokens_used_output
        pct = round(used / limit * 100, 1) if limit else 0
        color = "red" if pct >= 100 else ("orange" if pct >= 80 else "green")
        return format_html(
            '<span style="color: {};">{:,} / {:,} ({}%)</span>',
            color,
            used,
            limit,
            pct,
        )

    actions = ["reset_tokens", "activate_subscription"]

    @admin.action(description=_("Token hisoblagichni qayta tiklash"))
    def reset_tokens(self, request, queryset):
        from django.utils import timezone

        count = queryset.update(tokens_used_input=0, tokens_used_output=0, token_reset_at=timezone.now())
        self.message_user(request, f"{count} ta obunaning token hisoblagichi qayta tiklandi.")

    @admin.action(description=_("Tanlangan obunalarni faollashtirish"))
    def activate_subscription(self, request, queryset):
        from core.apps.api.enums.plan import PlanStatus

        count = queryset.update(status=PlanStatus.ACTIVE)
        self.message_user(request, f"{count} ta obuna faollashtirildi.")
