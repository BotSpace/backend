from django.db import models


class FileTypeEnum(models.TextChoices):
    FILE = "file"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
