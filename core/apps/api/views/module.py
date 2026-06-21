import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
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
    def refresh_manifest(self, request, pk=None):
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
