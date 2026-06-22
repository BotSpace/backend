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
    deploy_module,
    ensure_shared_deployment,
    fetch_manifest,
    get_project_module_manifests,
    get_project_modules_for_engine,
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

        # FAZA 2: trigger the Kaniko build job here. For now, acknowledge so the
        # GitHub → backend path can be verified end-to-end first.
        logger.info("github webhook: module %s push %s (build pending)", module.slug, (after or "")[:7])
        return Response({"ok": True, "module": module.slug, "sha": (after or "")[:7], "build": "pending"})
