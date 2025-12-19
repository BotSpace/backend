from typing import Optional
from core.apps.api.models.file import FileModel


def file_exists(uuid: str) -> bool:
    try:
        return FileModel.objects.filter(uuid=uuid).exists()
    except Exception:
        return False


def get_file_path(uuid: str) -> Optional[str]:
    try:
        return FileModel.objects.get(uuid=uuid).file
    except FileModel.DoesNotExist:
        return None
