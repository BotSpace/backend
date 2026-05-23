from django.db import models


class FieldKind(models.TextChoices):
    TEXT = "text", "Text"
    LONGTEXT = "longtext", "Long Text"
    INT = "int", "Integer"
    FLOAT = "float", "Float"
    BOOL = "bool", "Boolean"
    DATETIME = "datetime", "Date Time"
    DATE = "date", "Date"
    EMAIL = "email", "Email"
    URL = "url", "URL"
    PHONE = "phone", "Phone"
    ENUM = "enum", "Enum (choices)"
    JSON = "json", "JSON object"
    ARRAY = "array", "Array"
    RELATION = "relation", "Relation"
    FILE = "file", "File"
    IMAGE = "image", "Image"
    AUDIO = "audio", "Audio"
    VIDEO = "video", "Video"
    GEO = "geo", "Geo (lat,lng)"


class IndexKind(models.TextChoices):
    NONE = "none", "No index"
    ASC = "asc", "Ascending"
    DESC = "desc", "Descending"
    TEXT = "text", "Text search"
    HASHED = "hashed", "Hashed"
    UNIQUE = "unique", "Unique"
    TTL = "ttl", "TTL"


class CascadeMode(models.TextChoices):
    CASCADE = "cascade", "Cascade delete"
    RESTRICT = "restrict", "Restrict"
    SET_NULL = "set_null", "Set null"


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    RESTORE = "restore", "Restore"
    BULK_INSERT = "bulk_insert", "Bulk insert"
    BULK_UPDATE = "bulk_update", "Bulk update"
    BULK_DELETE = "bulk_delete", "Bulk delete"
    SCHEMA_CREATE = "schema_create", "Schema create"
    SCHEMA_UPDATE = "schema_update", "Schema update"
    SCHEMA_DELETE = "schema_delete", "Schema delete"


class WebhookEvent(models.TextChoices):
    DOC_CREATED = "doc.created", "Document created"
    DOC_UPDATED = "doc.updated", "Document updated"
    DOC_DELETED = "doc.deleted", "Document deleted"
    SCHEMA_CHANGED = "schema.changed", "Schema changed"
