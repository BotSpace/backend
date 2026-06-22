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


def _module_source(module: ModuleModel) -> dict:
    """Source config parsed from module.yaml, stored in manifest_cache['_source'].
    Returns {mode: 'github'|'endpoint', endpoint, github, dockerfile, port}.
    Defaults to github mode for legacy modules registered before module.yaml."""
    cache = module.manifest_cache or {}
    src = cache.get("_source") or {}
    if not src.get("mode"):
        src = {"mode": "github" if module.image else "endpoint", "endpoint": "", "github": module.github_url or ""}
    return src


def is_self_hosted(module: ModuleModel) -> bool:
    return _module_source(module).get("mode") == "endpoint"


def _shared_endpoint(module: ModuleModel) -> str:
    src = _module_source(module)
    if src.get("mode") == "endpoint" and src.get("endpoint"):
        return src["endpoint"]  # self-hosted: developer's own server
    return f"http://{_deployment_name(module.slug)}:{module.port}/rpc"


REGISTRY_BASE = "registry.iprogrammer.uz/botspace"


def register_module_from_yaml(yaml_text: str) -> tuple:
    """Parse a module.yaml and create/update the ModuleModel from it.

    module.yaml is the single source of truth — admin no longer enters fields by hand.
    Two source modes (mutually exclusive):
      source.github   → platform builds the image (Kaniko) and hosts the shared pod
      source.endpoint → self-hosted; engine connects to the developer's own server
    Returns (module, mode).
    """
    import yaml as _yaml

    try:
        data = _yaml.safe_load(yaml_text) or {}
    except Exception as exc:
        raise ManifestValidationError(f"module.yaml parse xatosi: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestValidationError("module.yaml noto'g'ri (obyekt kutilgan)")

    mod = data.get("module") or {}
    slug = str(mod.get("id") or "").strip()
    if not slug:
        raise ManifestValidationError("module.id majburiy")

    source = data.get("source") or {}
    runtime = data.get("runtime") or {}
    github = str(source.get("github") or "").strip()
    endpoint = str(source.get("endpoint") or "").strip()
    if not github and not endpoint:
        raise ManifestValidationError("source.github yoki source.endpoint majburiy")
    if github and endpoint:
        raise ManifestValidationError("source: faqat github YOKI endpoint bo'lsin (ikkalasi emas)")

    try:
        port = int(runtime.get("port") or 8100)
    except (TypeError, ValueError):
        port = 8100
    dockerfile = str(runtime.get("dockerfile") or "Dockerfile")

    if github:
        mode = "github"
        image = f"{REGISTRY_BASE}/module-{slug}:latest"
        github_url = github
    else:
        mode = "endpoint"
        image = ""
        github_url = ""

    module, _ = ModuleModel.objects.get_or_create(slug=slug, defaults={"name": mod.get("name") or slug, "image": image})
    module.name = mod.get("name") or slug
    module.description = mod.get("description") or ""
    module.icon = mod.get("icon") or ""
    module.github_url = github_url
    module.image = image
    module.port = port
    module.active = True
    cache = module.manifest_cache or {}
    cache["_source"] = {"mode": mode, "endpoint": endpoint, "github": github, "dockerfile": dockerfile, "port": port}
    module.manifest_cache = cache
    module.save()
    logger.info("Module registered from yaml: %s (mode=%s)", slug, mode)
    return module, mode


def module_status(module: ModuleModel) -> dict:
    """Live status for the admin panel: is the module up, building, or broken?"""
    src = _module_source(module)
    cache = module.manifest_cache or {}
    base = {
        "slug": module.slug,
        "mode": src.get("mode"),
        "active": module.active,
        "node_count": len(cache.get("nodes", []) or []),
        "manifest_fetched_at": module.manifest_fetched_at.isoformat() if module.manifest_fetched_at else None,
    }

    if src.get("mode") == "endpoint":
        endpoint = src.get("endpoint") or ""
        reachable = False
        try:
            resp = requests.post(
                endpoint,
                json={"jsonrpc": "2.0", "method": "describe", "params": {}, "id": 1},
                headers={"Authorization": f"Bearer {module.auth_token}"} if module.auth_token else {},
                timeout=3,
            )
            reachable = resp.ok
        except Exception:
            reachable = False
        base.update({"endpoint": endpoint, "reachable": reachable, "state": "running" if reachable else "error"})
        return base

    # github (platform-hosted): pod + last build job
    from core.apps.api.services.kubernetes_service import get_deployment_status, get_latest_module_build_status

    pod = get_deployment_status(_deployment_name(module.slug))  # running | init | stopped
    build = get_latest_module_build_status(module.slug)
    if build.get("status") == "running":
        state = "building"
    elif build.get("status") == "failed":
        state = "build_failed"
    elif pod == "running":
        state = "running"
    elif pod == "init":
        state = "deploying"
    else:
        state = "stopped"
    base.update({"pod": pod, "build": build, "state": state})
    return base


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
        if is_self_hosted(module):
            # Developer hosts the module on their own server — no pod to deploy.
            pm.service_id = ""
        else:
            ensure_shared_deployment(module)
            pm.service_id = _deployment_name(module.slug)
        pm.endpoint = _shared_endpoint(module)
        pm.status = "running"
        pm.enabled = True
        pm.save()
        logger.info("Module enabled: %s for project %s (%s)", module.slug, project.id,
                    "self-hosted" if is_self_hosted(module) else "shared pod")
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


def build_module_image(module: ModuleModel, sha: str = "", clone_url: str = "") -> str:
    """Kick off a Kaniko build Job for the module from its GitHub repo, then redeploy.

    Used by the GitHub webhook (auto-deploy) and the admin manual rebuild. Returns the
    Job name. The Job clones the repo, builds the image, pushes it, and POSTs the
    internal redeploy hook on success.
    """
    from django.conf import settings

    from core.apps.api.services.kubernetes_service import create_module_build_job

    image = (module.image or "").strip()
    if not image:
        raise ManifestValidationError(f"Module {module.slug} has no image configured")
    # Strip the :tag from the image to get the push base (tag lives in the last segment).
    last_segment = image.rsplit("/", 1)[-1]
    image_base = image.rsplit(":", 1)[0] if ":" in last_segment else image

    if not clone_url:
        gu = (module.github_url or "").strip().rstrip("/")
        if not gu:
            raise ManifestValidationError(f"Module {module.slug} has no github_url")
        clone_url = gu if gu.endswith(".git") else gu + ".git"

    return create_module_build_job(
        slug=module.slug,
        clone_url=clone_url,
        git_ref=sha or "default",
        image_base=image_base,
        sha=sha or "",
        dockerfile=_module_source(module).get("dockerfile") or "Dockerfile",
        internal_token=getattr(settings, "INTERNAL_API_TOKEN", "") or "",
        redeploy_url=f"http://web:8000/api/modules/{module.slug}/redeploy/",
    )


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
    if is_self_hosted(module):
        # No platform pod for self-hosted modules — nothing to tear down.
        logger.info("Module disabled for project %s (self-hosted, no pod)", project.id)
    elif not still_used:
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

    # credentialTypes — module declares its own credential type schemas.
    # Stored in manifest_cache["credential_types"] for later consumption by registry.
    credential_types = result.get("credentialTypes", [])
    if credential_types and not isinstance(credential_types, list):
        logger.warning("Module %s credentialTypes must be a list, ignoring", module.slug)
        credential_types = []
    # Namespace-enforce keys: each key must start with "{slug}." to avoid collisions.
    cleaned_cred_types = []
    for ct in credential_types:
        if not isinstance(ct, dict):
            continue
        key = ct.get("key", "")
        if not key.startswith(f"{module.slug}."):
            logger.warning(
                "Module %s credentialType key '%s' is not namespaced (must start with '%s.'), skipping",
                module.slug, key, module.slug,
            )
            continue
        cleaned_cred_types.append(ct)
    result["credential_types"] = cleaned_cred_types

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

    # Preserve the source config (mode/endpoint/dockerfile from module.yaml) — it
    # lives in manifest_cache['_source'] and must survive a describe() refresh.
    prev = module.manifest_cache or {}
    if prev.get("_source"):
        result["_source"] = prev["_source"]

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
