# type: ignore
"""
Plan admin configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from core.apps.api.models import PlanModel, ProjectPlanModel


@admin.register(PlanModel)
class PlanAdmin(ModelAdmin):
    """Tarif rejasi admin"""
    
    list_display = [
        'name_display',
        'price_display',
        'max_users',
        'features_display',
        'is_active',
        'order',
        'subscription_count',
    ]
    
    list_filter = ['is_active', 'powered_by_botmother']
    
    search_fields = ['name', 'description']
    
    ordering = ['order']
    
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('name', 'price', 'description', 'is_active', 'order')
        }),
        (_('Limitlar'), {
            'fields': ('max_users',)
        }),
        (_('Xususiyatlar'), {
            'fields': ('powered_by_botmother', 'custom_domain', 'priority_support')
        }),
    )
    
    @display(description=_('Tarif'))
    def name_display(self, obj):
        return obj.get_name_display()
    
    @display(description=_('Narx'))
    def price_display(self, obj):
        if obj.price == 0:
            return format_html('<span style="color: green; font-weight: bold;">BEPUL</span>')
        return format_html('<span style="font-weight: 500;">${}/oy</span>', obj.price)
    
    @display(description=_('Xususiyatlar'))
    def features_display(self, obj):
        features = []
        if not obj.powered_by_botmother:
            features.append('✓ No branding')
        if obj.custom_domain:
            features.append('✓ Custom domain')
        if obj.priority_support:
            features.append('✓ Priority support')
        return ', '.join(features) if features else '-'
    
    @display(description=_('Obunalar'))
    def subscription_count(self, obj):
        count = obj.subscriptions.count()
        return format_html(
            '<a href="/admin/api/projectplanmodel/?plan__id__exact={}" style="font-weight: 600;">{}</a>',
            obj.id,
            count
        )


@admin.register(ProjectPlanModel)
class ProjectPlanAdmin(ModelAdmin):
    """Proyekt tarifi admin"""
    
    list_display = [
        'project_name',
        'plan_name',
        'status_display',
        'users_display',
        'grace_period_info',
        'started_at',
    ]
    
    list_filter = ['status', 'plan__name', 'grace_period_notified']
    
    search_fields = ['project__name', 'project__owner__email']
    
    date_hierarchy = 'started_at'
    
    readonly_fields = [
        'current_users',
        'limit_exceeded_at',
        'grace_period_notified',
        'started_at',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('project', 'plan', 'status')
        }),
        (_('Statistika'), {
            'fields': ('current_users', 'limit_exceeded_at', 'grace_period_notified')
        }),
        (_('Sanalar'), {
            'fields': ('started_at', 'expires_at', 'created_at', 'updated_at')
        }),
    )
    
    @display(description=_('Proyekt'))
    def project_name(self, obj):
        return obj.project.name
    
    @display(description=_('Tarif'))
    def plan_name(self, obj):
        return obj.plan.get_name_display()
    
    @display(description=_('Holat'), ordering='status')
    def status_display(self, obj):
        colors = {
            'active': 'green',
            'grace_period': 'orange',
            'suspended': 'red',
            'cancelled': 'gray',
        }
        badges = {
            'active': '✓',
            'grace_period': '⚠',
            'suspended': '✗',
            'cancelled': '○',
        }
        color = colors.get(obj.status, 'black')
        badge = badges.get(obj.status, '')
        return format_html(
            '<span style="color: {}; font-weight: 600;">{} {}</span>',
            color,
            badge,
            obj.get_status_display()
        )
    
    @display(description=_('Foydalanuvchilar'))
    def users_display(self, obj):
        percentage = (obj.current_users / obj.plan.max_users * 100) if obj.plan.max_users else 0
        color = 'red' if percentage >= 100 else ('orange' if percentage >= 80 else 'green')
        
        # Progress bar style
        bar_width = min(percentage, 100)
        
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<span style="color: {}; font-weight: 600;">{}/{}</span>'
            '<div style="width: 60px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: {}; transition: width 0.3s;"></div>'
            '</div>'
            '<span style="color: {}; font-size: 11px;">{}%</span>'
            '</div>',
            color,
            obj.current_users,
            obj.plan.max_users,
            bar_width,
            color,
            color,
            int(percentage)
        )
    
    @display(description=_('Imkoniyat muddati'))
    def grace_period_info(self, obj):
        if not obj.limit_exceeded_at:
            return format_html('<span style="color: #9ca3af;">—</span>')
        
        from django.utils import timezone
        from datetime import timedelta
        
        grace_period_end = obj.limit_exceeded_at + timedelta(days=3)
        now = timezone.now()
        
        if now >= grace_period_end:
            return format_html('<span style="color: red; font-weight: 600;">⏰ TUGADI</span>')
        
        days_left = (grace_period_end - now).days
        return format_html(
            '<span style="color: orange; font-weight: 500;">⏳ {} kun qoldi</span>',
            days_left
        )
    
    actions = ['activate_plan', 'suspend_plan', 'reset_limit']
    
    @admin.action(description=_('Tanlangan tariflarni faollashtirish'))
    def activate_plan(self, request, queryset):
        """Activate selected plans"""
        from core.apps.api.enums.plan import PlanStatus
        
        count = queryset.update(
            status=PlanStatus.ACTIVE,
            limit_exceeded_at=None,
            grace_period_notified=False
        )
        self.message_user(request, f'{count} ta tarif faollashtirildi.')
    
    @admin.action(description=_('Tanlangan tariflarni to\'xtatish'))
    def suspend_plan(self, request, queryset):
        """Suspend selected plans"""
        from core.apps.api.enums.plan import PlanStatus
        
        count = queryset.update(status=PlanStatus.SUSPENDED)
        self.message_user(request, f'{count} ta tarif to\'xtatildi.')
    
    @admin.action(description=_('Limitni qayta tiklash'))
    def reset_limit(self, request, queryset):
        """Reset limit exceeded status"""
        count = queryset.update(
            limit_exceeded_at=None,
            grace_period_notified=False
        )
        self.message_user(request, f'{count} ta tarifning limiti qayta tiklandi.')
