import logging
from datetime import datetime, timezone

import requests

# Re-fetch a module's manifest from the running pod when the cached copy is older
# than this. Keeps node edits (sizes, fields, docs) flowing without a manual step.
MANIFEST_TTL_SECONDS = 120

from core.apps.api.models.module import ModuleModel, ProjectModuleModel
from core.apps.api.services.kubernetes_service import (
    create_deployment,
    create_service,
    delete_service,
    remove_deployment,
)

logger = logging.getLogger(__name__)

ALLOWED_FIELD_TYPES = {
    "text",
    "number",
    "textarea",
    "select",
    "checkbox",
    "switch",
    "description",
    "widget",
    "json",
    "color",
    "file",
    "datetime",
    "boolean",
    "code",
    "credential",
}


class ManifestValidationError(Exception):
    pass


def _deployment_name(module_slug: str) -> str:
    # SHARED across all projects — one pod per module (not per project).
    return f"module-{module_slug}".lower().replace("_", "-")


def _service_name(module_slug: str) -> str:
    return _deployment_name(module_slug)


def _shared_endpoint(module: ModuleModel) -> str:
    return f"http://{_deployment_name(module.slug)}:{module.port}/rpc"


def deploy_module(project, module: ModuleModel) -> ProjectModuleModel:
    """Enable a module for a project.

    Modules are SHARED: a single pod `module-{slug}` serves every project. Enabling
    a module just grants this project the right to use it (a ProjectModuleModel row
    pointing at the shared endpoint) and ensures the shared pod exists. The pod is
    idempotently created/updated, so concurrent enables are safe.
    """
    pm, _ = ProjectModuleModel.objects.get_or_create(
        project=project,
        module=module,
        defaults={"status": "pending"},
    )

    try:
        ensure_shared_deployment(module)
        pm.service_id = _deployment_name(module.slug)
        pm.endpoint = _shared_endpoint(module)
        pm.status = "running"
        pm.enabled = True
        pm.save()
        logger.info("Module enabled: %s for project %s (shared pod)", module.slug, project.id)
    except Exception as exc:
        pm.status = "failed"
        pm.save()
        logger.error("Module enable failed: %s / project %s: %s", module.slug, project.id, exc)
        raise

    return pm


def ensure_shared_deployment(module: ModuleModel) -> str:
    """Idempotently create/update the shared module pod + service. Returns its name."""
    dep_name = _deployment_name(module.slug)
    env_vars = [
        f"MODULE_SLUG={module.slug}",
        f"PORT={module.port}",
    ]
    if module.auth_token:
        env_vars.append(f"MODULE_AUTH_TOKEN={module.auth_token}")

    # No PROJECT_ID: the pod is shared; credentials are resolved by the engine and
    # passed per node.execute call, so the module needs no per-project identity.
    create_deployment(
        image=module.image,
        name=dep_name,
        env_vars=env_vars,
        container_port=module.port,
        readiness_path="/health",
        liveness_path="/health",
    )
    create_service(
        name=dep_name,
        deployment_name=dep_name,
        selector_labels={"app": "botmother-engine", "engine-name": dep_name},
        port=module.port,
    )
    return dep_name


def undeploy_module(project, module: ModuleModel) -> bool:
    """Disable a module for a project (revoke usage).

    The shared pod is kept while ANY other project still uses it; only the last
    project to disable tears down the shared deployment.
    """
    ProjectModuleModel.objects.filter(project=project, module=module).update(
        status="stopped",
        enabled=False,
    )

    still_used = (
        ProjectModuleModel.objects.filter(module=module, enabled=True)
        .exclude(project=project)
        .exists()
    )
    if not still_used:
        dep_name = _deployment_name(module.slug)
        remove_deployment(dep_name)
        delete_service(_service_name(module.slug))
        logger.info("Module shared pod removed (last user): %s", module.slug)
    else:
        logger.info("Module disabled for project %s; shared pod kept (other users)", project.id)
    return True


def fetch_manifest(module: ModuleModel) -> dict:
    # Shared model: the endpoint is deterministic; the pod exists once any project
    # has enabled the module (or admin deployed it).
    endpoint = _shared_endpoint(module)
    try:
        resp = requests.post(
            endpoint,
            json={"jsonrpc": "2.0", "method": "describe", "params": {}, "id": 1},
            headers={"Authorization": f"Bearer {module.auth_token}"} if module.auth_token else {},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("fetch_manifest failed for %s: %s", module.slug, exc)
        raise ManifestValidationError(f"describe call failed: {exc}") from exc

    result = data.get("result", data)

    nodes = result.get("nodes", [])
    for node in nodes:
        node_type = node.get("type", "")
        if not node_type.startswith(f"{module.slug}."):
            logger.warning("Module %s node type %s is not namespaced correctly", module.slug, node_type)

        for field in node.get("fields", []):
            field_type = field.get("type", "")
            if field_type and field_type not in ALLOWED_FIELD_TYPES:
                ProjectModuleModel.objects.filter(module=module, enabled=True).update(status="degraded")
                raise ManifestValidationError(
                    f"Module {module.slug}: unknown field type '{field_type}' in node '{node_type}'. "
                    f"Allowed: {sorted(ALLOWED_FIELD_TYPES)}"
                )

    try:
        docs_resp = requests.post(
            endpoint,
            json={"jsonrpc": "2.0", "method": "docs", "params": {}, "id": 2},
            headers={"Authorization": f"Bearer {module.auth_token}"} if module.auth_token else {},
            timeout=5,
        )
        docs_resp.raise_for_status()
        docs_data = docs_resp.json()
        docs_result = docs_data.get("result", {})
        result["docs"] = docs_result.get("markdown", "")
    except Exception as exc:
        logger.warning("fetch_manifest docs call failed for %s: %s", module.slug, exc)
        result.setdefault("docs", "")

    module.manifest_cache = result
    module.manifest_fetched_at = datetime.now(tz=timezone.utc)
    module.save(update_fields=["manifest_cache", "manifest_fetched_at"])

    return result


def get_project_module_manifests(project) -> list:
    enabled_pms = (
        ProjectModuleModel.objects.filter(project=project, enabled=True)
        .select_related("module")
    )

    # describe cache = {"module": {...}, "nodes": [NodeManifest, ...]}.
    # Constructor expects a FLAT array of node manifests, each tagged with its module.
    now = datetime.now(tz=timezone.utc)
    manifests = []
    for pm in enabled_pms:
        module = pm.module
        # TTL refresh (best-effort): pull the latest manifest when the cache is
        # stale so module edits propagate without a manual refresh.
        fetched = module.manifest_fetched_at
        if fetched is None or (now - fetched).total_seconds() > MANIFEST_TTL_SECONDS:
            try:
                fetch_manifest(module)
                module.refresh_from_db()
            except Exception as exc:
                logger.warning("manifest TTL refresh failed for %s: %s", module.slug, exc)
        cache = module.manifest_cache or {}
        for node in cache.get("nodes", []):
            node = dict(node)
            node["moduleSlug"] = module.slug
            node["moduleName"] = module.name
            manifests.append(node)

    return manifests


def get_project_modules_for_engine(project) -> list:
    enabled_pms = (
        ProjectModuleModel.objects.filter(project=project, enabled=True)
        .select_related("module")
    )

    result = []
    for pm in enabled_pms:
        module = pm.module
        cache = module.manifest_cache or {}
        nodes_raw = cache.get("nodes", [])
        node_types = [n.get("type") for n in nodes_raw if n.get("type")]
        # Per-node credential field keys (manifest fields live in `content`).
        # Engine reads this to resolve each credential_id and inject the decrypted
        # secret into node.execute as `credentials[field_key]`.
        credential_fields = {}
        for n in nodes_raw:
            ntype = n.get("type")
            if not ntype:
                continue
            keys = [
                f.get("key")
                for f in n.get("content", [])
                if f.get("type") == "credential" and f.get("key")
            ]
            if keys:
                credential_fields[ntype] = keys
        # Triggers are NODES flagged trigger:true / category=="triggers"; their
        # event/push mode comes from `triggerMode` (default event-match).
        trigger_types = [
            {"type": n.get("type"), "mode": n.get("triggerMode", "event-match")}
            for n in nodes_raw
            if n.get("type") and (n.get("trigger") or n.get("category") == "triggers")
        ]

        result.append(
            {
                "slug": module.slug,
                "endpoint": pm.endpoint or "",
                "auth_token": module.auth_token or "",
                "nodes": node_types,
                "triggers": trigger_types,
                "credential_fields": credential_fields,
            }
        )

    return result
