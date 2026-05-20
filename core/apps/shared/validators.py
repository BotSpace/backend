"""Project-wide file upload validators.

Centralised so any model/serializer that accepts a file can plug in
consistent size/MIME limits and we get a single place to tighten as
abuse patterns surface.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

MB = 1024 * 1024

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif"]
VIDEO_EXTENSIONS = ["mp4", "mov", "webm", "mkv"]
AUDIO_EXTENSIONS = ["mp3", "ogg", "wav", "m4a"]
DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "txt"]

MAX_IMAGE_SIZE = 10 * MB
MAX_VIDEO_SIZE = 50 * MB
MAX_AUDIO_SIZE = 25 * MB
MAX_DOCUMENT_SIZE = 25 * MB
MAX_AVATAR_SIZE = 5 * MB


def make_size_validator(max_bytes: int):
    """Return a validator that rejects files larger than ``max_bytes``."""

    def _validate(value):
        size = getattr(value, "size", None)
        if size is not None and size > max_bytes:
            raise ValidationError(
                _("File too large: %(size)d bytes (limit: %(limit)d).") % {"size": size, "limit": max_bytes}
            )

    return _validate


validate_image_size = make_size_validator(MAX_IMAGE_SIZE)
validate_video_size = make_size_validator(MAX_VIDEO_SIZE)
validate_audio_size = make_size_validator(MAX_AUDIO_SIZE)
validate_document_size = make_size_validator(MAX_DOCUMENT_SIZE)
validate_avatar_size = make_size_validator(MAX_AVATAR_SIZE)

image_extension_validator = FileExtensionValidator(IMAGE_EXTENSIONS)
video_extension_validator = FileExtensionValidator(VIDEO_EXTENSIONS)
audio_extension_validator = FileExtensionValidator(AUDIO_EXTENSIONS)
document_extension_validator = FileExtensionValidator(DOCUMENT_EXTENSIONS)
