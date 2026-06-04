from core.apps.api.models.project import ProjectModel
from core.apps.cms_legacy.enums.cms import FieldType
from core.apps.cms_legacy.models.cms import CollectionModel, FieldModel


def default_flow() -> dict:
    return {
        "nodes": [
            {
                "id": "node_1775417466338-5ek0gt09s",
                "type": "CommandTriggerNode",
                "position": {"x": 606, "y": 261},
                "data": {"command": "/start", "withArgs": False, "global": True},
                "width": 150,
                "height": 154,
                "selected": False,
                "positionAbsolute": {"x": 606, "y": 261},
                "dragging": False,
            },
            {
                "id": "node_1775417471071-a1fty8cde",
                "type": "EditOrSendMessageNode",
                "position": {"x": 891, "y": 234},
                "data": {
                    "messageText": "Assalomu Alaykum {{first_name}} botga xush kelibsiz<br><br>bot botspace.uz da yaratildi",
                    "keyboard": {
                        "active": "inline",
                        "inline": [
                            [
                                {
                                    "id": "btn-1775417488991",
                                    "text": "Bot yaratish",
                                    "type": "url",
                                    "value": "https://botspace.uz",
                                }
                            ]
                        ],
                        "reply": [],
                        "replyOptions": {
                            "remove_after_use": True,
                            "resize_keyboard": True,
                            "one_time_keyboard": False,
                            "is_persistent": False,
                        },
                    },
                },
                "width": 150,
                "height": 239,
                "selected": True,
                "positionAbsolute": {"x": 891, "y": 234},
                "dragging": False,
            },
        ],
        "edges": [
            {
                "source": "node_1775417466338-5ek0gt09s",
                "sourceHandle": "source-handler",
                "target": "node_1775417471071-a1fty8cde",
                "targetHandle": None,
                "type": "floating",
                "markerEnd": {"type": "arrow", "width": 30, "height": 30, "color": "#495057"},
                "style": {"strokeWidth": 4, "stroke": "#495057"},
                "animated": False,
                "id": "reactflow__edge-node_1775417466338-5ek0gt09ssource-handler-node_1775417471071-a1fty8cde",
            }
        ],
    }


USERS_COLLECTION_FIELDS = [
    # (name, label, type, required)
    ("chat_id", "Chat ID", FieldType.NUMBER.value, True),
    ("first_name", "Ism", FieldType.TEXT.value, False),
    ("last_name", "Familiya", FieldType.TEXT.value, False),
    ("username", "Username", FieldType.TEXT.value, False),
    ("last_seen", "Oxirgi faollik", FieldType.DATETIME.value, False),
    ("created_at", "Yaratilgan vaqt", FieldType.DATETIME.value, False),
]

CHAT_COLLECTION_FIELDS = [
    ("chat_id", "Chat ID", FieldType.TEXT.value, True),
    ("message", "Xabar", FieldType.TEXT.value, False),
    ("message_type", "Xabar turi", FieldType.TEXT.value, False),
    ("is_read", "O'qilgan", FieldType.BOOL.value, False),
    ("from_admin", "Admindan", FieldType.BOOL.value, False),
    ("updated_at", "Yangilangan vaqt", FieldType.DATETIME.value, False),
    ("created_at", "Yaratilgan vaqt", FieldType.DATETIME.value, False),
]

DEFAULT_COLLECTIONS = {
    "users": {
        "primary_field": "first_name",
        "fields": USERS_COLLECTION_FIELDS,
    },
    "chat": {
        "primary_field": "chat_id",
        "fields": CHAT_COLLECTION_FIELDS,
    },
}


def create_default_collections(project):
    """Loyiha uchun standart kolleksiyalarni yaratadi. Idempotent — get_or_create ishlatiladi."""
    for collection_name, meta in DEFAULT_COLLECTIONS.items():
        collection, created = CollectionModel.objects.get_or_create(
            name=collection_name,
            project=project,
            defaults={"user": project.owner},
        )

        if not created:
            continue

        fields = [
            FieldModel(
                collection=collection,
                name=field_name,
                type=field_type,
                required=required,
            )
            for field_name, _label, field_type, required in meta["fields"]
        ]
        FieldModel.objects.bulk_create(fields, ignore_conflicts=True)


def copy_collections(from_instance: ProjectModel, to_instance: ProjectModel):
    collections = from_instance.collections
    for collection in collections.all():
        instance, _ = CollectionModel.objects.get_or_create(
            name=collection.name, user=to_instance.owner, project=to_instance
        )
        fields = []
        for field in collection.fields.all():
            fields.append(
                FieldModel(
                    name=field.name,
                    collection=instance,
                    type=field.type,
                    default=field.default,
                    required=field.required,
                )
            )
        FieldModel.objects.bulk_create(fields)
