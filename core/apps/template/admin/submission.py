from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import display
from decimal import Decimal

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.models.template import TemplateModel
from core.apps.template.enums.template import TemplateSubmissionStatusEnum


@admin.register(TemplateSubmissionRequestModel)
class TemplateSubmissionRequestAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "user_phone",
        "project_name",
        "original_price",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = ("name", "user__phone", "project__name")
    readonly_fields = ("template", "reviewed_by", "reviewed_at", "created_at", "updated_at")
    autocomplete_fields = ["categories", "features"]
    
    fieldsets = (
        ("Submission Info", {
            "fields": (
                "user",
                "project",
                "name",
                "short_description",
                "description",
                "image",
                "video",
                "demo_url",
                "original_price",
            )
        }),
        ("Categories & Features", {
            "fields": (
                "categories",
                "features",
            )
        }),
        ("Review Info", {
            "fields": (
                "status",
                "rejection_reason",
                "template",
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
    
    actions = ["approve_submissions", "reject_submissions"]

    @display(description="User Phone")
    def user_phone(self, obj):
        return obj.user.phone if obj.user else "-"

    @display(description="Project Name")
    def project_name(self, obj):
        return obj.project.name if obj.project else "-"

    def save_model(self, request, obj, form, change):
        """Override save_model to handle status changes"""
        if change:  # Only for existing objects
            # Get the original object from database
            try:
                original_obj = TemplateSubmissionRequestModel.objects.get(pk=obj.pk)
                original_status = original_obj.status
            except TemplateSubmissionRequestModel.DoesNotExist:
                original_status = None
            
            # Check if status has changed
            if original_status and original_status != obj.status:
                # Status changed, update reviewed fields
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
                
                # If status changed to APPROVED and template doesn't exist yet, create it
                if obj.status == TemplateSubmissionStatusEnum.APPROVED.value and not obj.template:
                    # Create the template from the submission
                    template = TemplateModel.objects.create(
                        author=obj.user,
                        name=obj.name,
                        image=obj.image,
                        video=obj.video,
                        project=obj.project,
                        short_description=obj.short_description,
                        description=obj.description,
                        original_price=obj.original_price,
                        discount=Decimal("0.00"),
                        discount_type="percent",
                        demo_url=obj.demo_url,
                        is_verify=True,
                    )
                    
                    # Set many-to-many relationships
                    template.categories.set(obj.categories.all())
                    template.features.set(obj.features.all())
                    
                    # Link template to submission
                    obj.template = template
        
        super().save_model(request, obj, form, change)

    def approve_submissions(self, request, queryset):
        """Admin action to approve selected submissions"""
        approved_count = 0
        for submission in queryset:
            if submission.status == TemplateSubmissionStatusEnum.PENDING.value:
                # Create the template from the submission
                template = TemplateModel.objects.create(
                    author=submission.user,
                    name=submission.name,
                    image=submission.image,
                    video=submission.video,
                    project=submission.project,
                    short_description=submission.short_description,
                    description=submission.description,
                    original_price=submission.original_price,
                    discount=Decimal("0.00"),
                    discount_type="percent",
                    demo_url=submission.demo_url,
                    is_verify=True,
                )
                
                # Set many-to-many relationships
                template.categories.set(submission.categories.all())
                template.features.set(submission.features.all())
                
                # Update submission status
                submission.status = TemplateSubmissionStatusEnum.APPROVED.value
                submission.template = template
                submission.reviewed_by = request.user
                submission.reviewed_at = timezone.now()
                submission.save()
                approved_count += 1
        
        self.message_user(request, f"{approved_count} submission(s) approved successfully.")
    
    approve_submissions.short_description = "Approve selected submissions"

    def reject_submissions(self, request, queryset):
        """Admin action to reject selected submissions"""
        rejected_count = 0
        for submission in queryset:
            if submission.status == TemplateSubmissionStatusEnum.PENDING.value:
                submission.status = TemplateSubmissionStatusEnum.REJECTED.value
                submission.rejection_reason = "Rejected by admin via bulk action"
                submission.reviewed_by = request.user
                submission.reviewed_at = timezone.now()
                submission.save()
                rejected_count += 1
        
        self.message_user(request, f"{rejected_count} submission(s) rejected.")
    
    reject_submissions.short_description = "Reject selected submissions"
