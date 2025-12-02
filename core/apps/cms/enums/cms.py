from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class FieldType(TextChoices):
    TEXT = "text", _("Text")
    NUMBER = "number", _("Number")
    BOOL = "bool", _("bool")
    DATETIME = "datetime", _("datetime")
    FILE = "file", _("file")
    AUDIO = "audio", _("audio")
    VIDEO = "video", _("video")
    PHOTO = "photo", _("photo")
    RELATION = "relation", _("Relation")
