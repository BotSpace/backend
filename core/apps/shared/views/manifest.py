"""Global built-in node manifest endpoint (project-siz).

Agent (va boshqa dasturlar) built-in node schema'lari uchun shu yagona manbadan
oladi: `GET /api/v1/shared/manifest/builtin-nodes/`. Modul manifestlari per-project
bo'lgani uchun alohida (`/project/{id}/node-manifests/` unified). Built-in
manifestlar maxfiy emas (constructor baribir browserga beradi) → AllowAny.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.apps.api.services.node_manifest_service import get_builtin_node_manifests


@api_view(["GET"])
@permission_classes([AllowAny])
def builtin_node_manifests_view(request):
    return Response({"manifests": get_builtin_node_manifests()})
