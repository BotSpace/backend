"""Template spec builder — project'dan JSONB snapshot yaratadi.

Xavfsizlik qoidalari:
- Credential secret qiymati HECH QACHON spec'ga kirmaydi.
- Flow snapshot'dagi real credential_id'lar "cred:<logical_key>" placeholder bilan almashtiriladi.
"""
from __future__ import annotations

import copy
import json
import logging
import re

logger = logging.getLogger(__name__)

# Flow node'laridagi credential_id maydonlari (string yoki int bo'lishi mumkin)
_CRED_FIELD = "credential_id"
# Placeholder prefix
_CRED_PLACEHOLDER_PREFIX = "cred:"


def _extract_env_keys_from_flow(flow) -> list[str]:
    """Flow JSON'dan {{env.KEY}} pattern'larini topib, KEY larni qaytaradi."""
    if not flow:
        return []
    text = json.dumps(flow)
    return list(dict.fromkeys(re.findall(r"\{\{env\.([A-Z][A-Z0-9_]{0,63})\}\}", text)))


def _walk_nodes(flow) -> list[dict]:
    """Flow'dan node list'ini xavfsiz chiqaradi."""
    if isinstance(flow, dict):
        nodes = flow.get("nodes", [])
    elif isinstance(flow, list):
        nodes = flow
    else:
        return []
    return [n for n in nodes if isinstance(n, dict)]


def _find_credential_ids_in_flow(flow) -> set[int]:
    """Flow'dagi barcha real credential_id (int) larni topadi."""
    ids = set()
    for node in _walk_nodes(flow):
        data = node.get("data") or {}
        cid = data.get(_CRED_FIELD)
        if isinstance(cid, int):
            ids.add(cid)
        elif isinstance(cid, str) and cid.isdigit():
            ids.add(int(cid))
    return ids


def _build_credential_key_map(credential_ids: set[int]) -> dict[int, str]:
    """credential_id → logical key mapping. Format: "cred_<type_key>_<id>"."""
    if not credential_ids:
        return {}
    try:
        from core.apps.credentials.models.credential import Credential
        creds = Credential.objects.filter(id__in=credential_ids, deleted_at__isnull=True).only(
            "id", "type_key", "name"
        )
        result = {}
        for c in creds:
            # Logical key: type_key yetarli, bir type'dan ko'p bo'lsa name qo'shiladi
            result[c.id] = c.type_key
        # Bir xil type_key'lar bo'lsa, name bilan farqlaymiz
        seen_types: dict[str, list[int]] = {}
        for cid, tkey in result.items():
            seen_types.setdefault(tkey, []).append(cid)
        for tkey, cids in seen_types.items():
            if len(cids) > 1:
                for cid in cids:
                    cred = next(c for c in creds if c.id == cid)
                    safe_name = re.sub(r"[^a-z0-9_]", "_", cred.name.lower())[:32]
                    result[cid] = f"{tkey}_{safe_name}"
        return result
    except Exception:
        logger.exception("_build_credential_key_map failed")
        return {}


def _replace_credential_ids_in_flow(flow, key_map: dict[int, str]):
    """Flow deepcopy'sida real credential_id'larni placeholder bilan almashtiradi."""
    flow = copy.deepcopy(flow)
    for node in _walk_nodes(flow):
        data = node.get("data")
        if not isinstance(data, dict):
            continue
        cid = data.get(_CRED_FIELD)
        cid_int = None
        if isinstance(cid, int):
            cid_int = cid
        elif isinstance(cid, str) and cid.isdigit():
            cid_int = int(cid)
        if cid_int is not None and cid_int in key_map:
            data[_CRED_FIELD] = f"{_CRED_PLACEHOLDER_PREFIX}{key_map[cid_int]}"
    return flow


def _build_credentials_spec(key_map: dict[int, str], credential_ids: set[int]) -> list[dict]:
    """Credential type'larini credential registry'dan olib, spec.credentials ro'yxatini yaratadi."""
    if not key_map:
        return []
    try:
        from core.apps.credentials.models.credential import Credential
        from core.apps.credentials.registry import get_type

        creds = {c.id: c for c in Credential.objects.filter(
            id__in=credential_ids, deleted_at__isnull=True
        ).only("id", "type_key", "name")}

        result = []
        for cid, logical_key in key_map.items():
            cred = creds.get(cid)
            if not cred:
                continue
            type_info = get_type(cred.type_key) or {}
            result.append({
                "key": logical_key,
                "type": cred.type_key,
                "label": type_info.get("label", cred.type_key),
                "required": True,
                "description": f"{type_info.get('label', cred.type_key)} credential",
            })
        return result
    except Exception:
        logger.exception("_build_credentials_spec failed")
        return []


def _build_collections_spec(project) -> list[dict]:
    """Project'ning cmsv2 collection schema + catalog data'sini JSONB'ga serialize qiladi."""
    try:
        from core.apps.cms.models.collection import Collection
        from core.apps.cms.services import mongo as cms_mongo
        from core.apps.api.services.project import collection_is_catalog, NEVER_COPY_DATA

        collections = []
        flow = getattr(project, "flow", None)

        qs = Collection.objects.filter(
            project=project, deleted_at__isnull=True
        ).prefetch_related("fields").order_by("id")

        for col in qs:
            fields_spec = []
            for f in col.fields.all():
                fields_spec.append({
                    "name": f.name,
                    "label": f.label,
                    "kind": f.kind,
                    "required": f.required,
                    "default": f.default,
                    "validators": f.validators or {},
                    "order": f.order,
                })

            data = []
            if col.name not in NEVER_COPY_DATA and collection_is_catalog(flow, col.name):
                try:
                    docs = cms_mongo.find(project.id, col.name, limit=100000, include_deleted=False)
                    for doc in (docs or []):
                        clean = {
                            k: v for k, v in doc.items()
                            if not k.startswith("_")
                        }
                        data.append(clean)
                except Exception:
                    logger.exception("_build_collections_spec: mongo read failed for %s", col.name)

            collections.append({
                "name": col.name,
                "label": col.label,
                "description": col.description,
                "primary_field": col.primary_field,
                "system": col.system,
                "fields": fields_spec,
                "data": data,
            })

        return collections
    except Exception:
        logger.exception("_build_collections_spec failed")
        return []


def _build_modules_spec(project) -> list[dict]:
    """Project'ning enabled modullarini slug'lari bilan ro'yxatlaydi."""
    try:
        from core.apps.api.models.module import ProjectModuleModel
        result = []
        for pm in ProjectModuleModel.objects.filter(
            project=project, enabled=True
        ).select_related("module"):
            result.append({
                "slug": pm.module.slug,
                "required": True,
            })
        return result
    except Exception:
        logger.exception("_build_modules_spec failed")
        return []


def build_spec_from_project(project) -> dict:
    """Project'dan to'liq template spec snapshot'ini yaratadi.

    XAVFSIZLIK: credential secret qiymatlari HECH QACHON spec'ga kirmaydi.
    Flow'dagi real credential_id'lar logical placeholder bilan almashtiriladi.
    """
    flow = getattr(project, "flow", None) or {}

    # Credential placeholder almashtirish
    cred_ids = _find_credential_ids_in_flow(flow)
    key_map = _build_credential_key_map(cred_ids)
    flow_snapshot = _replace_credential_ids_in_flow(flow, key_map)

    # Env key'larni flow'dan aniqla
    env_keys = _extract_env_keys_from_flow(flow)
    envs = [{"key": k, "label": "", "required": True, "description": ""} for k in env_keys]

    return {
        "flow": flow_snapshot,
        "collections": _build_collections_spec(project),
        "credentials": _build_credentials_spec(key_map, cred_ids),
        "modules": _build_modules_spec(project),
        "envs": envs,
    }


def apply_spec_to_project(spec: dict, new_project, credential_map: dict[str, int]) -> None:
    """Spec'dan yangi project uchun collections, modules'ni sozlaydi.

    credential_map: {"logical_key": credential_id} — user tomonidan berilgan mapping.
    Flow'dagi placeholder'lar real id'ga almashtirilishi uchun bu mapping ishlatiladi.
    """
    _install_collections(spec.get("collections", []), new_project)
    _install_modules(spec.get("modules", []), new_project)


def replace_placeholders_in_flow(flow, credential_map: dict[str, int]):
    """Flow'dagi "cred:<key>" placeholder'larni real credential_id'larga almashtiradi."""
    flow = copy.deepcopy(flow)
    for node in _walk_nodes(flow):
        data = node.get("data")
        if not isinstance(data, dict):
            continue
        cid = data.get(_CRED_FIELD)
        if isinstance(cid, str) and cid.startswith(_CRED_PLACEHOLDER_PREFIX):
            logical_key = cid[len(_CRED_PLACEHOLDER_PREFIX):]
            if logical_key in credential_map:
                data[_CRED_FIELD] = credential_map[logical_key]
    return flow


def _install_collections(collections_spec: list[dict], project) -> None:
    """Spec'dan cmsv2 collection'larni yaratadi va catalog data'ni insert qiladi."""
    if not collections_spec:
        return
    try:
        from core.apps.cms.models.collection import Collection
        from core.apps.cms.models.field import Field
        from core.apps.cms.services import mongo as cms_mongo

        owner_id = getattr(project, "owner_id", None)

        for col_spec in collections_spec:
            name = col_spec.get("name", "")
            if not name:
                continue
            existing = Collection.objects.filter(
                project=project, name=name, deleted_at__isnull=True
            ).first()
            if existing is None:
                col = Collection.objects.create(
                    project=project,
                    owner_id=owner_id,
                    name=name,
                    label=col_spec.get("label", ""),
                    description=col_spec.get("description", ""),
                    primary_field=col_spec.get("primary_field", ""),
                    system=col_spec.get("system", False),
                )
                fields = []
                for f in col_spec.get("fields", []):
                    fields.append(Field(
                        collection=col,
                        name=f["name"],
                        label=f.get("label", ""),
                        kind=f.get("kind", "text"),
                        required=f.get("required", False),
                        default=f.get("default"),
                        validators=f.get("validators") or {},
                        order=f.get("order", 0),
                    ))
                if fields:
                    Field.objects.bulk_create(fields, ignore_conflicts=True)
            else:
                col = existing

            # Data faqat catalog collection uchun va faqat bo'sh bo'lsa
            data = col_spec.get("data", [])
            if data and cms_mongo.count(project.id, name) == 0:
                docs = [dict(d) for d in data]
                cms_mongo.insert_many(project.id, name, docs)

    except Exception:
        logger.exception("_install_collections failed for project=%s", getattr(project, "id", None))


def _install_modules(modules_spec: list[dict], project) -> None:
    """Spec'dagi slug'lar bo'yicha modullarni project'ga enable qiladi."""
    if not modules_spec:
        return
    try:
        from core.apps.api.models.module import ModuleModel, ProjectModuleModel

        slugs = [m["slug"] for m in modules_spec if m.get("slug")]
        if not slugs:
            return
        modules = {m.slug: m for m in ModuleModel.objects.filter(slug__in=slugs, active=True)}

        for slug in slugs:
            module = modules.get(slug)
            if module is None:
                logger.warning("_install_modules: slug %r topilmadi yoki active emas, skip", slug)
                continue
            ProjectModuleModel.objects.get_or_create(
                project=project,
                module=module,
                defaults={"enabled": True, "config": {}, "status": "pending"},
            )
    except Exception:
        logger.exception("_install_modules failed for project=%s", getattr(project, "id", None))
