# type: ignore
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.env import env
from core.apps.api.models import ProjectModel, WebhookEndpointModel
from core.services.response import error_response, success_response


def _hook_url(token) -> str:
    return "https://%s/api/hook/%s/" % (env.str("DOMAIN", "api.botspace.uz"), token)


class WebhookEndpointMintView(APIView):
    """POST /api/webhook/endpoint/  body: {project, node_id}

    Owner-only. Idempotent per (project, node_id): a node mints its URL once and
    reuses it forever (the constructor caches it in node data). Returns {token, url}.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project")
        node_id = (request.data.get("node_id") or "").strip()
        if not project_id or not node_id:
            return error_response({"detail": "project va node_id majburiy"}, status.HTTP_400_BAD_REQUEST)

        try:
            project = ProjectModel.objects.get(pk=project_id)
        except (ProjectModel.DoesNotExist, ValueError, TypeError):
            return error_response({"detail": "Project topilmadi"}, status.HTTP_404_NOT_FOUND)
        if project.owner_id != request.user.id:
            return error_response({"detail": "Ruxsat yo'q"}, status.HTTP_403_FORBIDDEN)

        endpoint, _ = WebhookEndpointModel.objects.get_or_create(project=project, node_id=node_id)
        return success_response({"token": str(endpoint.token), "url": _hook_url(endpoint.token)})


class WebhookHookResolveView(APIView):
    """GET /api/internal/webhook-hook/<uuid:token>/  (X-Internal-Token)

    For the Go webhook service: token -> routing info. The service forwards the
    incoming request to the project's running engine (bot-<release/debug uuid>).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        expected = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not expected or request.headers.get("X-Internal-Token", "") != expected:
            return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            endpoint = WebhookEndpointModel.objects.select_related("project").get(token=token)
        except WebhookEndpointModel.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        project = endpoint.project
        return Response(
            {
                "token": str(endpoint.token),
                "node_id": endpoint.node_id,
                "project_id": project.id,
                "release_webhook_uuid": str(project.release_webhook_uuid),
                "debug_webhook_uuid": str(project.debug_webhook_uuid),
            },
            status=status.HTTP_200_OK,
        )
