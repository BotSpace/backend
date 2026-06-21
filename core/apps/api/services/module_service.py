import logging
from datetime import datetime, timezone

import requests

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
}


class ManifestValidationError(Exception):
    pass


def _deployment_name(module_slug: str, project_id: int) -> str:
    return f"module-{module_slug}-{project_id}".lower().replace("_", "-")


def _service_name(module_slug: str, project_id: int) -> str:
    return _deployment_name(module_slug, project_id)


def deploy_module(project, module: ModuleModel) -> ProjectModuleModel:
    pm, _ = ProjectModuleModel.objects.get_or_create(
        project=project,
        module=module,
        defaults={"status": "pending"},
    )

    dep_name = _deployment_name(module.slug, project.id)
    env_vars = [
        f"MODULE_SLUG={module.slug}",
        f"PROJECT_ID={project.id}",
        f"PORT={module.port}",
    ]
    if module.auth_token:
        env_vars.append(f"MODULE_AUTH_TOKEN={module.auth_token}")

    try:
        # Modules listen on their own port and only expose /health (not /ready).
        create_deployment(
            image=module.image,
            name=dep_name,
            env_vars=env_vars,
            project_id=project.id,
            container_port=module.port,
            readiness_path="/health",
            liveness_path="/health",
        )

        selector_labels = {
            "app": "botmother-engine",
            "engine-name": dep_name,
        }
        create_service(
            name=dep_name,
            deployment_name=dep_name,
            selector_labels=selector_labels,
            port=module.port,
        )

        endpoint = f"http://{dep_name}:{module.port}/rpc"
        pm.service_id = dep_name
        pm.endpoint = endpoint
        pm.status = "running"
        pm.enabled = True
        pm.save()
        logger.info("Module deployed: %s for project %s", module.slug, project.id)
    except Exception as exc:
        pm.status = "failed"
        pm.save()
        logger.error("Module deploy failed: %s / project %s: %s", module.slug, project.id, exc)
        raise

    return pm


def undeploy_module(project, module: ModuleModel) -> bool:
    dep_name = _deployment_name(module.slug, project.id)
    svc_name = _service_name(module.slug, project.id)

    remove_deployment(dep_name)
    delete_service(svc_name)

    ProjectModuleModel.objects.filter(project=project, module=module).update(
        status="stopped",
        enabled=False,
    )
    logger.info("Module undeployed: %s for project %s", module.slug, project.id)
    return True


def fetch_manifest(module: ModuleModel) -> dict:
    pm_qs = ProjectModuleModel.objects.filter(module=module, enabled=True).first()
    if pm_qs is None or not pm_qs.endpoint:
        raise ManifestValidationError(f"No active endpoint for module {module.slug}")

    endpoint = pm_qs.endpoint
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
                pm_qs and ProjectModuleModel.objects.filter(module=module, enabled=True).update(status="degraded")
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
    manifests = []
    for pm in enabled_pms:
        module = pm.module
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
            }
        )

    return result
