from rest_framework import serializers
from core.apps.cms_legacy.models import ExportTaskModel


class ExportCollectionSerializer(serializers.Serializer):
    """Serializer for initiating collection export"""
    pass


class ExportTaskStatusSerializer(serializers.ModelSerializer):
    """Serializer for export task status"""
    
    file_url = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ExportTaskModel
        fields = [
            "task_id",
            "status",
            "file_url",
            "file_path",
            "error_message",
            "total_records",
            "processed_records",
            "progress_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
    
    def get_file_url(self, obj):
        """Get full URL for download"""
        if obj.file_path and obj.status == ExportTaskModel.Status.COMPLETED:
            request = self.context.get("request")
            if request:
                from django.conf import settings
                return request.build_absolute_uri(f"{settings.MEDIA_URL}{obj.file_path}")
        return None
    
    def get_progress_percentage(self, obj):
        """Calculate progress percentage"""
        if obj.total_records and obj.total_records > 0:
            return round((obj.processed_records / obj.total_records) * 100, 2)
        return 0.0
