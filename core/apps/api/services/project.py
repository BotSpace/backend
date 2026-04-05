from core.apps.api.models.project import ProjectModel
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models.cms import CollectionModel, FieldModel


def default_flow() -> dict:
    return {
        "flow": {
            "nodes": [
                {
                    "id": "node_1775417466338-5ek0gt09s",
                    "type": "CommandTriggerNode",
                    "position": {"x": 606, "y": 261},
                    "data": {"command": "", "withArgs": False, "global": True},
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
