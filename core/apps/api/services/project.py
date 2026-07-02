import logging

from core.apps.api.models.project import ProjectModel
from core.apps.cms_legacy.enums.cms import FieldType
from core.apps.cms_legacy.models.cms import CollectionModel, FieldModel

logger = logging.getLogger(__name__)


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


# ── cmsv2 (new CMS) template copy ────────────────────────────────────────────

# Collections that must NEVER receive copied data (runtime/user data only).
NEVER_COPY_DATA = {"users", "chat"}
# Collections that are always system schemas.
SYSTEM_COLLECTION_NAMES = {"users", "chat"}

# Flow node types that READ a collection (catalog candidates).
_LOAD_NODE_TYPES = {"LoadCollectionListNode", "LoadCollectionItemNode"}
# Flow node types that WRITE a collection (disqualifies it from being a catalog).
_WRITE_NODE_TYPES = {"CollectionNode", "UpdateCollectionNode", "DeleteCollectionNode"}


def _flow_nodes(flow) -> list:
    """Defensively extract the node list from a flow (dict or list)."""
    if isinstance(flow, dict):
        nodes = flow.get("nodes", [])
    elif isinstance(flow, list):
        nodes = flow
    else:
        nodes = []
    return [n for n in nodes if isinstance(n, dict)]


def _node_collection_name(data: dict) -> str | None:
    """Pull the referenced collection name out of a node's `data` dict.

    Supports both `collection_name` (flat) and `collection.name`/`collection: str`.
    """
    if not isinstance(data, dict):
        return None
    name = data.get("collection_name")
    if isinstance(name, str) and name:
        return name
    coll = data.get("collection")
    if isinstance(coll, dict):
        cname = coll.get("name")
        if isinstance(cname, str) and cname:
            return cname
    elif isinstance(coll, str) and coll:
        return coll
    return None


def _iter_collection_data_names(obj):
    """Node data ichida ixtiyoriy chuqurlikdagi `collectionData.collection`
    havolalarini topadi — inline keyboard tugmalari kolleksiyadan render
    bo'lganda o'qish hisoblanadi (Load* node bo'lmasa ham)."""
    if isinstance(obj, dict):
        cd = obj.get("collectionData")
        if isinstance(cd, dict):
            c = cd.get("collection")
            if isinstance(c, str) and c:
                yield c
        for v in obj.values():
            yield from _iter_collection_data_names(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_collection_data_names(v)


def collection_is_catalog(flow, name: str) -> bool:
    """A collection is a CATALOG (static data to copy) when the flow READS it
    (via a Load* node OR an inline-keyboard `collectionData` listing) and never
    WRITES it (via a Collection save/update/delete node).

    Pure function over the flow JSON — no Mongo access — so it is unit-testable.
    `users`/`chat` are never catalogs.
    """
    if name in NEVER_COPY_DATA:
        return False

    read = False
    write = False
    for node in _flow_nodes(flow):
        ntype = node.get("type")
        data = node.get("data", {})
        cname = _node_collection_name(data)
        if cname == name:
            if ntype in _LOAD_NODE_TYPES:
                read = True
            elif ntype in _WRITE_NODE_TYPES:
                write = True
        # collectionData tugma-ro'yxatlari — top-level collection nomidan qat'i nazar
        if not read and name in _iter_collection_data_names(data):
            read = True

    return read and not write


def _new_fields_from_source_collection(src_collection, target_collection):
    """Build cmsv2 Field rows from a source cmsv2 Collection's fields."""
    from core.apps.cms.models.field import Field

    fields = []
    for f in src_collection.fields.all():
        fields.append(
            Field(
                collection=target_collection,
                name=f.name,
                label=f.label,
                kind=f.kind,
                required=f.required,
                default=f.default,
                validators=f.validators or {},
                order=f.order,
            )
        )
    return fields


def _new_fields_from_legacy_collection(legacy_collection, target_collection):
    """Build cmsv2 Field rows from a legacy CollectionModel's fields.

    Legacy types are NOT mapped — everything becomes a safe TEXT field.
    """
    from core.apps.cms.enums import FieldKind
    from core.apps.cms.models.field import Field

    fields = []
    for i, f in enumerate(legacy_collection.fields.all()):
        fields.append(
            Field(
                collection=target_collection,
                name=f.name,
                kind=FieldKind.TEXT,
                required=bool(f.required),
                order=i,
            )
        )
    return fields


def _new_fields_from_sample(sample_doc, target_collection):
    """Infer cmsv2 Field rows from a sample Mongo document (non `_` keys)."""
    from core.apps.cms.enums import FieldKind
    from core.apps.cms.models.field import Field

    fields = []
    if not isinstance(sample_doc, dict):
        return fields
    order = 0
    for key in sample_doc:
        if not isinstance(key, str) or key.startswith("_"):
            continue
        fields.append(
            Field(
                collection=target_collection,
                name=key,
                kind=FieldKind.TEXT,
                order=order,
            )
        )
        order += 1
    return fields


def copy_cms_collections(from_project, to_project, flow=None):
    """Register the SOURCE project's collections in the NEW CMS for `to_project`
    and copy MongoDB DATA for CATALOG collections only.

    Defensive: never raises out in a way that would break project creation.
    Idempotent: existing cmsv2 collections are skipped.
    """
    from core.apps.cms.models.collection import Collection
    from core.apps.cms.models.field import Field
    from core.apps.cms.services import mongo as cms_mongo

    flow = flow if flow is not None else getattr(from_project, "flow", None)

    # Collection nomlarini registry'dan (MongoDB'dan emas) yig'amiz. Template'ning
    # kontent collection'lari LEGACY registry'da, shuning uchun ikkalasini birlashtiramiz.
    try:
        names: set[str] = set()
        names.update(
            CollectionModel.objects.filter(project=from_project).values_list("name", flat=True)
        )
        names.update(
            from_project.cms_collections.filter(deleted_at__isnull=True).values_list("name", flat=True)
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception("copy_cms_collections: failed to list source collections (project=%s)", from_project.id)
        return

    owner_id = getattr(to_project, "owner_id", None) or getattr(to_project, "user_id", None)

    for name in names:
        if not isinstance(name, str) or name.startswith("system."):
            continue
        try:
            existing = Collection.objects.filter(
                project=to_project, name=name, deleted_at__isnull=True
            ).first()
            if existing is None:
                is_system = name in SYSTEM_COLLECTION_NAMES

                # Resolve a source cmsv2 collection (preferred) for label/primary_field.
                src_cms = from_project.cms_collections.filter(name=name, deleted_at__isnull=True).first()
                src_legacy = CollectionModel.objects.filter(project=from_project, name=name).first()

                label = ""
                primary_field = ""
                description = ""
                if src_cms is not None:
                    label = src_cms.label
                    primary_field = src_cms.primary_field
                    description = src_cms.description

                target = Collection.objects.create(
                    project=to_project,
                    owner_id=owner_id,
                    name=name,
                    label=label,
                    description=description,
                    primary_field=primary_field,
                    system=is_system,
                )

                # Derive fields: cmsv2 source → legacy source → sample doc.
                if src_cms is not None:
                    new_fields = _new_fields_from_source_collection(src_cms, target)
                elif src_legacy is not None:
                    new_fields = _new_fields_from_legacy_collection(src_legacy, target)
                else:
                    sample = (cms_mongo.find(from_project.id, name, limit=1) or [None])[0]
                    new_fields = _new_fields_from_sample(sample, target)

                if new_fields:
                    Field.objects.bulk_create(new_fields, ignore_conflicts=True)
            # else: schema already present — leave as-is (idempotent).

            # ── Copy DATA only for CATALOG collections ──────────────────────
            if name in NEVER_COPY_DATA:
                continue
            if not collection_is_catalog(flow, name):
                continue

            # Guard against double-insert (idempotent re-run).
            if cms_mongo.count(to_project.id, name) != 0:
                continue

            docs = cms_mongo.find(from_project.id, name, limit=100000, include_deleted=False)
            if not docs:
                continue

            # Strip storage-managed keys so Mongo assigns a FRESH `_id` and the
            # data layer re-stamps metadata + tags the NEW tenant. Preserving
            # `_id` would collide in the shared collection.
            for doc in docs:
                for k in ("_id", "_project_id", "_created_at", "_updated_at", "_version", "_deleted_at"):
                    doc.pop(k, None)

            cms_mongo.insert_many(to_project.id, name, docs)
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "copy_cms_collections: failed for collection %r (from=%s to=%s)",
                name,
                from_project.id,
                to_project.id,
            )
            continue
