# type: ignore
import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.apps.api.models.project import ProjectModel
from core.apps.api.services.kubernetes_service import get_pod_ips_by_label


def _internal_token_ok(request) -> bool:
    expected = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not expected:
        return False
    provided = request.headers.get("X-Internal-Token", "")
    return hmac.compare_digest(str(provided), str(expected))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def credential_by_id(request, pk):
    """Resolve and decrypt a credential for the engine.

    Headers:
      X-Internal-Token: <settings.INTERNAL_API_TOKEN>
      X-Project-Id:     <project id> — used for cross-tenant owner guard

    Returns:
      200 { id, name, type_key, mode, data:{...decrypted...} }
      401 if token is missing or invalid
      403 if credential.owner != project.owner (cross-tenant guard)
      404 if missing/soft-deleted
    """
    if not _internal_token_ok(request):
        return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    from core.apps.credentials.models import Credential
    from core.apps.credentials.registry import get_type
    from core.apps.credentials.services import crypto

    try:
        cred = Credential.objects.select_related("owner").get(pk=pk, deleted_at__isnull=True)
    except Credential.DoesNotExist:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    # Cross-tenant owner guard
    project_id = request.headers.get("X-Project-Id")
    if project_id:
        try:
            project = ProjectModel.objects.get(pk=project_id)
        except ProjectModel.DoesNotExist:
            return Response({"detail": "Project not found"}, status=status.HTTP_403_FORBIDDEN)
        if project.owner_id != cred.owner_id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        decrypted = crypto.decrypt(cred.data_encrypted)
    except Exception:
        return Response({"detail": "Decryption error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    type_info = get_type(cred.type_key) or {}
    mode = type_info.get("mode")

    # For oauth2 credentials: refresh token if expired, inject fresh access_token
    if mode == "oauth2":
        try:
            from core.apps.credentials.services.oauth import get_valid_access_token
            fresh_token = get_valid_access_token(cred)
            decrypted["access_token"] = fresh_token
        except Exception as exc:
            return Response(
                {"detail": f"Token refresh failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {
            "id": cred.id,
            "name": cred.name,
            "type_key": cred.type_key,
            "mode": mode,
            "data": decrypted,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def project_by_release_uuid(request, uuid):
    """Get project information by release webhook UUID

    This endpoint is used by the Golang webhook service to get project info.
    """
    if not _internal_token_ok(request):
        return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        project = ProjectModel.objects.get(release_webhook_uuid=uuid)
        release = project.release
        version = release.version if release else 1
        podIPs = get_pod_ips_by_label(f"engine-name=release-{project.id}-{version}")
        if len(podIPs) <= 0:
            podIP = "None"
        else:
            podIP = podIPs[0]
        return Response(
            {
                "id": project.id,
                "ip": podIP,
                "release_webhook_uuid": str(project.release_webhook_uuid),
                "debug_webhook_uuid": str(project.debug_webhook_uuid),
                "release_version": version,
            },
            status=status.HTTP_200_OK,
        )
    except ProjectModel.DoesNotExist:
        return Response(
            {"error": "Project not found"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def project_by_debug_uuid(request, uuid):
    """Get project information by debug webhook UUID

    This endpoint is used by the Golang webhook service to get project info.
    """
    if not _internal_token_ok(request):
        return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        project = ProjectModel.objects.get(debug_webhook_uuid=uuid)
        podIPs = get_pod_ips_by_label(f"engine-name=debug-{project.id}")
        if len(podIPs) <= 0:
            podIP = "None"
        else:
            podIP = podIPs[0]
        return Response(
            {
                "id": project.id,
                "ip": podIP,
                "release_webhook_uuid": str(project.release_webhook_uuid),
                "debug_webhook_uuid": str(project.debug_webhook_uuid),
            },
            status=status.HTTP_200_OK,
        )
    except ProjectModel.DoesNotExist:
        return Response(
            {"error": "Project not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
