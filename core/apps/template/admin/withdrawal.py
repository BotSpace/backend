from django.contrib import admin
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.contrib.auth import get_user_model
from unfold.admin import ModelAdmin
from unfold.decorators import display

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum

User = get_user_model()


@admin.register(TemplateWithdrawalRequestModel)
class TemplateWithdrawalRequestAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_phone",
        "amount",
        "card_number",
        "card_owner",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = ("user__phone", "card_number", "card_owner")
    readonly_fields = ("reviewed_by", "reviewed_at", "created_at", "updated_at")
    
    fieldsets = (
        ("Withdrawal Info", {
            "fields": (
                "user",
                "amount",
                "card_number",
                "card_owner",
            )
        }),
        ("Review Info", {
            "fields": (
                "status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )
    
    actions = ["approve_withdrawals", "reject_withdrawals"]

    @display(description="User Phone")
    def user_phone(self, obj):
        return obj.user.phone if obj.user else "-"

    def save_model(self, request, obj, form, change):
        """Override save_model to handle status changes and balance deduction"""
        if change:  # Only for existing objects
            # Get the original object from database
            try:
                original_obj = TemplateWithdrawalRequestModel.objects.get(pk=obj.pk)
                original_status = original_obj.status
            except TemplateWithdrawalRequestModel.DoesNotExist:
                original_status = None
            
            # Check if status has changed
            if original_status and original_status != obj.status:
                # Status changed, update reviewed fields
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
                
                # If status changed to APPROVED, deduct from user's template balance
                if obj.status == WithdrawalStatusEnum.APPROVED.value and original_status != WithdrawalStatusEnum.APPROVED.value:
                    # Use atomic transaction to prevent race conditions
                    with transaction.atomic():
                        # Lock the user row for update
                        user = User.objects.select_for_update().get(pk=obj.user.pk)
                        if user.template_balance >= obj.amount:
                            # Use F() expression for atomic update
                            User.objects.filter(pk=user.pk).update(
                                template_balance=F('template_balance') - obj.amount
                            )
                        else:
                            # If insufficient balance, reject the withdrawal
                            obj.status = WithdrawalStatusEnum.REJECTED.value
                            obj.rejection_reason = "Insufficient template balance at approval time"
        
        super().save_model(request, obj, form, change)

    def approve_withdrawals(self, request, queryset):
        """Admin action to approve selected withdrawal requests"""
        approved_count = 0
        for withdrawal in queryset.select_for_update():
            if withdrawal.status == WithdrawalStatusEnum.PENDING.value:
                # Use atomic transaction to prevent race conditions
                with transaction.atomic():
                    # Lock the user row for update
                    user = User.objects.select_for_update().get(pk=withdrawal.user.pk)
                    if user.template_balance >= withdrawal.amount:
                        # Deduct from template balance using F() expression
                        User.objects.filter(pk=user.pk).update(
                            template_balance=F('template_balance') - withdrawal.amount
                        )
                        
                        # Update withdrawal status
                        withdrawal.status = WithdrawalStatusEnum.APPROVED.value
                        withdrawal.reviewed_by = request.user
                        withdrawal.reviewed_at = timezone.now()
                        withdrawal.save()
                        approved_count += 1
                    else:
                        # Mark as rejected due to insufficient balance
                        withdrawal.status = WithdrawalStatusEnum.REJECTED.value
                        withdrawal.rejection_reason = "Insufficient template balance"
                        withdrawal.reviewed_by = request.user
                        withdrawal.reviewed_at = timezone.now()
                        withdrawal.save()
        
        self.message_user(request, f"{approved_count} withdrawal request(s) approved successfully.")
    
    approve_withdrawals.short_description = "Approve selected withdrawal requests"

    def reject_withdrawals(self, request, queryset):
        """Admin action to reject selected withdrawal requests"""
        rejected_count = 0
        for withdrawal in queryset:
            if withdrawal.status == WithdrawalStatusEnum.PENDING.value:
                withdrawal.status = WithdrawalStatusEnum.REJECTED.value
                withdrawal.rejection_reason = "Rejected by admin via bulk action"
                withdrawal.reviewed_by = request.user
                withdrawal.reviewed_at = timezone.now()
                withdrawal.save()
                rejected_count += 1
        
        self.message_user(request, f"{rejected_count} withdrawal request(s) rejected.")
    
    reject_withdrawals.short_description = "Reject selected withdrawal requests"
