import os
import logging
from typing import Optional
from datetime import datetime
from celery import shared_task
from django.conf import settings
from bson import ObjectId

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def export_collection_to_excel(self, task_id: str):
    """
    Export collection data to Excel file
    
    Args:
        task_id: UUID of ExportTaskModel
    """
    from core.apps.cms.models import ExportTaskModel
    from core.apps.cms.services.mongo import get_repository
    
    try:
        # Get export task
        export_task = ExportTaskModel.objects.get(task_id=task_id)
        export_task.status = ExportTaskModel.Status.PROCESSING
        export_task.save(update_fields=["status", "updated_at"])
        
        collection = export_task.collection
        
        # Get MongoDB repository
        repo = get_repository(collection)
        
        # Count total documents
        total_records = repo.count({})
        export_task.total_records = total_records
        export_task.save(update_fields=["total_records", "updated_at"])
        
        # Prepare export directory
        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{collection.name}_{timestamp}_{task_id}.xlsx"
        file_path = os.path.join(export_dir, filename)
        
        # Fetch data in batches to avoid memory issues
        batch_size = 1000
        all_data = []
        skip = 0
        
        logger.info(f"Starting export for collection {collection.name}, total records: {total_records}")
        
        while skip < total_records:
            batch_data = repo.find(where={}, limit=batch_size, skip=skip)
            
            # Convert ObjectId to string for Excel export
            for item in batch_data:
                if "_id" in item and isinstance(item["_id"], ObjectId):
                    item["_id"] = str(item["_id"])
            
            all_data.extend(batch_data)
            skip += batch_size
            
            # Update progress
            export_task.processed_records = min(skip, total_records)
            export_task.save(update_fields=["processed_records", "updated_at"])
            
            logger.info(f"Processed {export_task.processed_records}/{total_records} records")
        
        # Create Excel file
        if all_data:
            try:
                import openpyxl
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill
                
                wb = Workbook()
                ws = wb.active
                ws.title = collection.name[:31]  # Excel sheet name max 31 chars
                
                # Get all unique keys from all documents
                all_keys = set()
                for item in all_data:
                    all_keys.update(item.keys())
                
                # Sort keys, put _id first
                headers = sorted(all_keys)
                if "_id" in headers:
                    headers.remove("_id")
                    headers.insert(0, "_id")
                
                # Write headers with styling
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                
                for col_idx, header in enumerate(headers, start=1):
                    cell = ws.cell(row=1, column=col_idx, value=header)
                    cell.font = header_font
                    cell.fill = header_fill
                
                # Write data rows
                for row_idx, item in enumerate(all_data, start=2):
                    for col_idx, header in enumerate(headers, start=1):
                        value = item.get(header, "")
                        
                        # Handle various data types
                        if isinstance(value, (dict, list)):
                            value = str(value)
                        elif isinstance(value, datetime):
                            value = value.isoformat()
                        
                        ws.cell(row=row_idx, column=col_idx, value=value)
                
                # Auto-adjust column widths
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Max width 50
                    ws.column_dimensions[column_letter].width = adjusted_width
                
                # Save workbook
                wb.save(file_path)
                logger.info(f"Excel file saved: {file_path}")
                
            except ImportError:
                # Fallback to pandas if openpyxl not available
                import pandas as pd
                df = pd.DataFrame(all_data)
                df.to_excel(file_path, index=False, engine='openpyxl')
                logger.info(f"Excel file saved using pandas: {file_path}")
        else:
            # Create empty Excel file
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = collection.name[:31]
            ws.cell(row=1, column=1, value="No data available")
            wb.save(file_path)
        
        # Update task status
        export_task.file_path = f"exports/{filename}"
        export_task.status = ExportTaskModel.Status.COMPLETED
        export_task.processed_records = total_records
        export_task.save(update_fields=["file_path", "status", "processed_records", "updated_at"])
        
        logger.info(f"Export completed successfully: {task_id}")
        return {"status": "success", "file_path": export_task.file_path}
        
    except ExportTaskModel.DoesNotExist:
        logger.error(f"Export task not found: {task_id}")
        raise
    
    except Exception as e:
        logger.exception(f"Export failed for task {task_id}: {str(e)}")
        
        try:
            export_task = ExportTaskModel.objects.get(task_id=task_id)
            export_task.status = ExportTaskModel.Status.FAILED
            export_task.error_message = str(e)
            export_task.save(update_fields=["status", "error_message", "updated_at"])
        except:
            pass
        
        # Retry if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        
        raise
