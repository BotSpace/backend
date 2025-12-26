# type: ignore
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.apps.api.models.project import ProjectModel
from core.apps.api.services.kubernetes_service import get_pod_ips_by_label


@api_view(["GET"])
@permission_classes([AllowAny])
def project_by_release_uuid(request, uuid):
    """Get project information by release webhook UUID

    This endpoint is used by the Golang webhook service to get project info.
    """
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
