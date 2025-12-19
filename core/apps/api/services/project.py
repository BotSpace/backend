# type: ignore
from core.apps.api.models.project import ProjectModel
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models.cms import CollectionModel, FieldModel


def default_flow() -> dict:
    return {
        "nodes": [
            {
                "id": "node_0",
                "type": "CommandTriggerNode",
                "position": {"x": -63.47046493902432, "y": 208.63414634146335},
                "data": {"context": {}, "node_type": "CommandTriggerNode", "global": True, "command": "/start"},
                "width": 320,
                "height": 236,
            },
            {
                "id": "node_1",
                "type": "SendTextMessageNode",
                "position": {"x": -118.60948932926817, "y": 579.7048780487804},
                "data": {
                    "recipients": {"sendToSender": True, "additionalIds": []},
                    "keyboard": {
                        "active": "inline",
                        "inline": [
                            [
                                {
                                    "id": "btn-1765521805822",
                                    "text": "Bot yaratish",
                                    "type": "url",
                                    "value": "https://botspace.uz",
                                }
                            ]
                        ],
                        "reply": [],
                    },
                    "messageText": "Assalomu Alaykum {{first_name}} botga xush kelibsiz\n\nbot botspace.uz da yaratildi",
                    "parseMode": "HTML",
                    "disableNotification": False,
                    "protectContent": False,
                },
                "width": 400,
                "height": 480,
                "selected": True,
                "positionAbsolute": {"x": -118.60948932926817, "y": 579.7048780487804},
                "dragging": False,
            },
        ],
        "edges": [
            {
                "source": "node_0",
                "sourceHandle": "source-handler",
                "target": "node_1",
                "targetHandle": "target-handler",
                "type": "step",
                "markerEnd": {"type": "arrow", "width": 30, "height": 30, "color": "#495057"},
                "style": {"strokeWidth": 1.5, "stroke": "#495057"},
                "animated": False,
                "id": "reactflow__edge-node_0source-handler-node_1target-handler",
            }
        ],
    }


def create_default_collections(project):
    collections = {
        "users": {
            "fields": {
                "chat_id": {
                    "type": FieldType.TEXT.value,
                    "required": True,
                    "default": None,
                },
                "first_name": {
                    "type": FieldType.TEXT.value,
                    "required": True,
                },
                "last_name": {
                    "type": FieldType.TEXT.value,
                    "required": False,
                },
                "updated_at": {
                    "type": FieldType.DATETIME.value,
                    "required": True,
                },
                "created_at": {
                    "type": FieldType.DATETIME.value,
                    "required": True,
                },
            }
        },
        "chat": {
            "fields": {
                "chat_id": {
                    "type": FieldType.TEXT.value,
                    "required": True,
                },
                "message": {
                    "type": FieldType.TEXT.value,
                    "required": False,
                },
                "message_type": {
                    "type": FieldType.TEXT.value,
                    "required": False,
                },
                "is_read": {
                    "type": FieldType.BOOL.value,
                    "default": False,
                },
                "from_admin": {
                    "type": FieldType.BOOL.value,
                    "default": False,
                },
                "updated_at": {
                    "type": FieldType.DATETIME.value,
                    "required": False,
                },
                "created_at": {
                    "type": FieldType.DATETIME.value,
                    "required": False,
                },
            }
        },
    }
    for collection_name, collection_data in collections.items():
        collection = CollectionModel.objects.create(
            name=collection_name,
            user=project.owner,
            project=project,
        )

        fields = []
        for field_name, field_props in collection_data["fields"].items():
            fields.append(
                FieldModel(
                    collection=collection,
                    name=field_name,
                    type=field_props["type"],
                    required=field_props.get("required", False),
                    default=field_props.get("default"),
                )
            )

        FieldModel.objects.bulk_create(fields)


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
