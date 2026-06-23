"""Module-scoped file upload/delete endpoint.

Auth: Bearer <project_id>:<hex(HMAC-SHA256(INTERNAL_API_TOKEN, project_id))>

Only POST (upload) and DELETE are exposed. GET (retrieve) stays on the public
/api/file/<uuid>/ endpoint (AllowAny, existing FileView).
"""
import hashlib
import hmac as hmac_lib

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.api.models import FileModel
from core.apps.api.models.project import ProjectModel
from core.apps.api.serializers.file import ModuleFileCreateSerializer


def _verify_module_token(request):
    """Return (project, None) on success or (None, error_response) on failure."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, Response({"detail": "Missing Bearer token"}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header[len("Bearer "):]
    parts = token.split(":", 1)
    if len(parts) != 2:
        return None, Response({"detail": "Invalid token format"}, status=status.HTTP_401_UNAUTHORIZED)

    project_id, provided_hmac = parts[0], parts[1]

    internal_token = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not internal_token:
        return None, Response({"detail": "Server misconfigured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    expected_hmac = hmac_lib.new(
        internal_token.encode(),
        project_id.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac_lib.compare_digest(provided_hmac.lower(), expected_hmac.lower()):
        return None, Response({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        project = ProjectModel.objects.select_related("owner").get(pk=project_id)
    except (ProjectModel.DoesNotExist, ValueError):
        return None, Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    return project, None


@extend_schema(tags=["module-file"])
class ModuleFileUploadView(APIView):
    """POST /api/module-file/ — fayl yuklash (HMAC-scoped token talab qilinadi)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        project, err = _verify_module_token(request)
        if err is not None:
            return err

        serializer = ModuleFileCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        instance = serializer.save(user=project.owner, project=project)
        return Response(
            {
                "uuid": str(instance.uuid),
                "file": request.build_absolute_uri(instance.file.url),
                "filetype": instance.filetype,
                "filesize": instance.filesize,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["module-file"])
class ModuleFileDeleteView(APIView):
    """DELETE /api/module-file/<uuid>/ — faylni o'chirish (faqat o'z project'niki bo'lsa)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request, uuid):
        project, err = _verify_module_token(request)
        if err is not None:
            return err

        try:
            file_obj = FileModel.objects.get(uuid=uuid, project=project)
        except FileModel.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        file_obj.file.delete(save=False)
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
