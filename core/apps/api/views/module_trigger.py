import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from config.env import env
from core.apps.api.exceptions.wabhook import WebhookConnectionError, WebhookInvalidStatusCode
from core.apps.api.models.project import ProjectModel
from core.apps.api.services.webhook import service_send_webhook
from core.services.response import error_response, success_response

logger = logging.getLogger(__name__)


class ModuleTriggerView(APIView):
    """
    POST /api/module-trigger/<project_uuid>/
    Internal endpoint: modul → engine trigger relay.
    X-Internal-Token header bilan himoyalangan.
    """

    permission_classes = [AllowAny]

    def post(self, request, project_uuid):
        token = request.headers.get("X-Internal-Token", "")
        expected = env.str("INTERNAL_API_TOKEN", default="")
        if expected and token != expected:
            return error_response({"detail": "Unauthorized"}, status.HTTP_401_UNAUTHORIZED)

        try:
            project = ProjectModel.objects.get(uuid=project_uuid)
        except ProjectModel.DoesNotExist:
            return error_response({"detail": "Project not found"}, status.HTTP_404_NOT_FOUND)

        release = project.release
        if release is None or not release.service_id:
            return error_response({"detail": "No active release"}, status.HTTP_404_NOT_FOUND)

        try:
            service_send_webhook(release.service_id, request.data)
        except (WebhookConnectionError, WebhookInvalidStatusCode) as exc:
            logger.error("module_trigger relay failed project=%s: %s", project_uuid, exc)
            return error_response({"detail": str(exc)})

        return success_response({"detail": "ok"})
