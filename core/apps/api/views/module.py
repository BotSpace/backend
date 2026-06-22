import hashlib
import hmac
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.apps.api.models.module import ModuleModel, ProjectModuleModel
from core.apps.api.serializers.module import (
    CreateModuleSerializer,
    EnableModuleSerializer,
    ModuleSerializer,
    ProjectModuleSerializer,
)
from core.apps.api.services.module_service import (
    ManifestValidationError,
    build_module_image,
    deploy_module,
    ensure_shared_deployment,
    fetch_manifest,
    get_project_module_manifests,
    get_project_modules_for_engine,
    register_module_from_yaml,
    undeploy_module,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["modules"])
class ModuleViewSet(ModelViewSet):
    queryset = ModuleModel.objects.all().order_by("-id")
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = ModuleSerializer
    lookup_field = "slug"  # detail/retrieve by slug (constructor uses slug)
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["id", "name", "created_at", "manifest_fetched_at"]
    ordering = ["-id"]

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(active=(active == "true"))
        return qs

    def get_permissions(self):
        # Browsing the catalog is open to any authenticated user (they enable
        # per-project); only mutating the catalog stays admin-only.
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CreateModuleSerializer
        return ModuleSerializer

    @extend_schema(summary="Barcha modullar katalogi (admin)")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Modul yaratish (admin)")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Modulni yangilash (admin)")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Modulni o'chirish (admin)")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(summary="Modul detail (authenticated)")
    def retrieve(self, request, *args, **kwargs):
        module = self.get_object()
        cache = module.manifest_cache or {}
        if not cache.get("docs") and not cache.get("nodes"):
            try:
                fetch_manifest(module)
                module.refresh_from_db()
            except Exception as exc:
                logger.warning("retrieve pre-warm failed for %s: %s", module.slug, exc)
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Manifest yangilash (admin)")
    @action(methods=["POST"], detail=True, url_path="refresh-manifest", url_name="refresh-manifest")
    def refresh_manifest(self, request, slug=None):
        module = self.get_object()
        try:
            manifest = fetch_manifest(module)
        except ManifestValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"manifest": manifest})

    @extend_schema(summary="Modul live status (pod/build/endpoint)")
    @action(methods=["GET"], detail=True, url_path="status", url_name="status")
    def status_view(self, request, slug=None):
        from core.apps.api.services.module_service import module_status

        module = self.get_object()
        return Response(module_status(module))

    @extend_schema(summary="module.yaml dan modul ro'yxatga olish (admin)")
    @action(methods=["POST"], detail=False, url_path="register-yaml", url_name="register-yaml")
    def register_yaml(self, request):
        """Register/update a module from its module.yaml (paste or raw URL).

        github mode → trigger a build; endpoint (self-hosted) mode → fetch manifest now.
        """
        yaml_text = request.data.get("yaml")
        yaml_url = request.data.get("yaml_url")
        if yaml_url and not yaml_text:
            try:
                import requests as _rq

                resp = _rq.get(yaml_url, timeout=10)
                resp.raise_for_status()
                yaml_text = resp.text
            except Exception as exc:
                return Response({"detail": f"yaml_url o'qib bo'lmadi: {exc}"}, status=status.HTTP_400_BAD_REQUEST)
        if not yaml_text:
            return Response({"detail": "yaml yoki yaml_url majburiy"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            module, mode = register_module_from_yaml(yaml_text)
        except ManifestValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        info = {}
        try:
            if mode == "github":
                info["build_job"] = build_module_image(module)
            else:
                fetch_manifest(module)
                info["manifest"] = "fetched"
        except Exception as exc:
            info["warning"] = str(exc)

        data = ModuleSerializer(module).data
        return Response({"ok": True, "mode": mode, "module": data, **info}, status=status.HTTP_201_CREATED)


def _resolve_project_for_user(user, pk):
    from core.apps.api.models import ProjectModel
    from core.apps.cms.views._common import resolve_project

    project = resolve_project(pk)
    if project is None:
        return None
    if project.owner_id != user.id:
        return None
    return project


def project_module_list(request, project):
    pms = (
        ProjectModuleModel.objects.filter(project=project)
        .select_related("module")
        .order_by("-id")
    )
    return Response(ProjectModuleSerializer(pms, many=True).data)


def project_module_enable(request, project):
    ser = EnableModuleSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    slug = ser.validated_data["module_slug"]
    module = get_object_or_404(ModuleModel, slug=slug, active=True)

    if ProjectModuleModel.objects.filter(project=project, module=module, enabled=True).exists():
        return Response({"detail": "already enabled"}, status=status.HTTP_200_OK)

    try:
        pm = deploy_module(project, module)
    except Exception as exc:
        logger.error("deploy_module error: %s", exc)
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        fetch_manifest(module)
    except ManifestValidationError as exc:
        logger.warning("fetch_manifest after deploy: %s", exc)

    return Response(ProjectModuleSerializer(pm).data, status=status.HTTP_201_CREATED)


def project_module_disable(request, project, slug):
    module = get_object_or_404(ModuleModel, slug=slug)
    pm = get_object_or_404(ProjectModuleModel, project=project, module=module)

    try:
        undeploy_module(project, module)
    except Exception as exc:
        logger.error("undeploy_module error: %s", exc)
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    pm.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def project_module_manifests_view(request, project):
    manifests = get_project_module_manifests(project)
    return Response({"manifests": manifests})


def project_modules_for_engine_view(request, project):
    data = get_project_modules_for_engine(project)
    return Response({"modules": data})


def project_module_register_self_hosted(request, project):
    """Foydalanuvchi O'Z self-hosted modulini ro'yxatga oladi.

    Body: { "endpoint": "https://...", "name": "...", "auth_token": "..." }
    Javob: ProjectModuleSerializer(pm).data
    """
    import re
    import uuid as _uuid

    from core.apps.api.services.module_service import ManifestValidationError, deploy_module, fetch_manifest

    endpoint = (request.data.get("endpoint") or "").strip()
    name = (request.data.get("name") or "").strip()
    auth_token = (request.data.get("auth_token") or "").strip() or None

    if not endpoint:
        return Response({"detail": "endpoint majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    # URL formatini tekshir — https:// yoki http:// bilan boshlanishi shart
    if not re.match(r"^https?://", endpoint):
        return Response({"detail": "endpoint to'g'ri URL bo'lishi kerak (http:// yoki https://)"}, status=status.HTTP_400_BAD_REQUEST)

    # Slug: name berilsa undan, aks holda endpoint host'idan hosil qilinadi
    if name:
        slug_base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    else:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        slug_base = re.sub(r"[^a-z0-9]+", "-", parsed.netloc.lower()).strip("-") or "self-hosted"

    # Bir xil endpoint bo'lsa mavjud modulni topamiz (yaratmaymiz)
    existing = None
    for m in ModuleModel.objects.filter(active=True):
        src = (m.manifest_cache or {}).get("_source") or {}
        if src.get("mode") == "endpoint" and src.get("endpoint") == endpoint:
            existing = m
            break

    if existing is None:
        # Slug uniqueness: agar slug band bo'lsa UUID suffix qo'shiladi
        slug = slug_base[:80]
        if ModuleModel.objects.filter(slug=slug).exists():
            slug = f"{slug_base[:70]}-{str(_uuid.uuid4())[:8]}"

        module = ModuleModel(
            slug=slug,
            name=name or slug,
            image="",
            port=8100,
            active=True,
        )
        if auth_token:
            module.auth_token = auth_token
        module.manifest_cache = {
            "_source": {"mode": "endpoint", "endpoint": endpoint}
        }
        module.save()
        logger.info("Self-hosted module created: slug=%s endpoint=%s project=%s", slug, endpoint, project.id)
    else:
        module = existing
        # name yoki auth_token yangilansa update qilish
        changed = False
        if name and module.name != name:
            module.name = name
            changed = True
        if auth_token and module.auth_token != auth_token:
            module.auth_token = auth_token
            changed = True
        if changed:
            module.save(update_fields=["name", "auth_token", "updated_at"])

    # Endpoint'dan manifest olish — javob bermasa 400 qaytariladi
    try:
        fetch_manifest(module)
    except ManifestValidationError as exc:
        # Agar modul yangi yaratilgan bo'lsa, uni o'chirib tashlaymiz (cleanup)
        if existing is None:
            module.delete()
        return Response(
            {"detail": f"Modul endpoint ulanmadi: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ProjectModuleModel ga ulash (self-hosted uchun pod yaratilmaydi)
    try:
        pm = deploy_module(project, module)
    except Exception as exc:
        logger.error("deploy_module (self-hosted) error: %s", exc)
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(ProjectModuleSerializer(pm).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["modules"], summary="CI redeploy hook (X-Internal-Token)")
class ModuleRedeployView(APIView):
    """Auto-deploy hook: a module's GitHub CI pushed a new image → restart the
    shared pod (re-pulls :latest) and refresh the manifest.

    Auth: shared X-Internal-Token (== settings.INTERNAL_API_TOKEN), same as the
    debug/internal endpoints. No user session — the module CI calls this.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request, slug):
        expected = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not expected or request.headers.get("X-Internal-Token", "") != expected:
            return Response({"detail": "Ruxsat etilmagan so'rov."}, status=status.HTTP_403_FORBIDDEN)

        module = get_object_or_404(ModuleModel, slug=slug)
        try:
            ensure_shared_deployment(module)  # Recreate the pod → pulls the new :latest image.
        except Exception as exc:
            logger.error("module redeploy %s failed: %s", slug, exc)
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Manifest refresh is best-effort: the pod is restarting (Recreate), so the
        # describe RPC may fail right now. The 120s TTL refresh picks up the new
        # manifest once the pod is ready.
        try:
            fetch_manifest(module)
            refreshed = True
        except Exception as exc:
            logger.info("module redeploy %s: manifest refresh deferred (pod restarting): %s", slug, exc)
            refreshed = False

        return Response({"ok": True, "module": slug, "manifest_refreshed": refreshed})


def _normalize_repo(url: str) -> str:
    return (url or "").strip().rstrip("/").lower().removesuffix(".git")


def _match_module_by_repo(html_url: str, clone_url: str, full_name: str):
    """Find the ModuleModel whose github_url points at the pushed repo."""
    candidates = {_normalize_repo(x) for x in (html_url, clone_url) if x}
    fn = (full_name or "").lower()
    for m in ModuleModel.objects.exclude(github_url=""):
        gu = _normalize_repo(m.github_url)
        if not gu:
            continue
        if gu in candidates or (fn and gu.endswith(fn)):
            return m
    return None


def _github_webhook_secret() -> str:
    from core.apps.shared.utils.settings import get_config

    val = get_config("github", "module_webhook_secret")
    if isinstance(val, (list, tuple)):
        val = val[0] if val else ""
    return val or getattr(settings, "GITHUB_WEBHOOK_SECRET", "")


@extend_schema(tags=["modules"], summary="GitHub App webhook (module auto-deploy)")
class GitHubModuleWebhookView(APIView):
    """GitHub App push webhook → build & deploy the matching module.

    Verifies X-Hub-Signature-256 (HMAC-SHA256, webhook secret). On a default-branch
    push, matches the repo to a registered module (by github_url) and triggers a
    build. The webhook secret lives in DB config (github/module_webhook_secret) so
    no env/deploy change is needed.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        secret = _github_webhook_secret()
        if not secret:
            logger.error("github webhook: secret not configured")
            return Response({"detail": "webhook not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        signature = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("github webhook: invalid signature")
            return Response({"detail": "invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        event = request.headers.get("X-GitHub-Event", "")
        if event == "ping":
            return Response({"ok": True, "pong": True})
        if event != "push":
            return Response({"ok": True, "ignored_event": event})

        payload = request.data or {}
        repo = payload.get("repository", {}) or {}
        ref = payload.get("ref", "")
        after = payload.get("after", "")
        default_branch = repo.get("default_branch", "main")

        if ref != f"refs/heads/{default_branch}":
            return Response({"ok": True, "ignored_ref": ref})

        module = _match_module_by_repo(repo.get("html_url", ""), repo.get("clone_url", ""), repo.get("full_name", ""))
        if module is None:
            logger.info("github webhook: no module for repo %s", repo.get("full_name"))
            return Response({"ok": True, "no_module_for": repo.get("full_name", "")})

        # Build the image from the pushed commit; the Job redeploys on success.
        try:
            job = build_module_image(module, sha=after, clone_url=repo.get("clone_url", ""))
        except Exception as exc:
            logger.error("github webhook: build trigger failed for %s: %s", module.slug, exc)
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.info("github webhook: module %s push %s → build job %s", module.slug, (after or "")[:7], job)
        return Response({"ok": True, "module": module.slug, "sha": (after or "")[:7], "build_job": job})
