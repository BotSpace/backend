import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel


class ExportTaskModel(AbstractBaseModel):
    """Model to track collection export tasks"""
    
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
    
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    collection = models.ForeignKey("CollectionModel", on_delete=models.CASCADE, related_name="exports")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file_path = models.CharField(max_length=500, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    total_records = models.IntegerField(null=True, blank=True)
    processed_records = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.collection.name} - {self.task_id}"
    
    class Meta:
        db_table = "export_task"
        verbose_name = _("Export Task")
        verbose_name_plural = _("Export Tasks")
        ordering = ["-created_at"]
