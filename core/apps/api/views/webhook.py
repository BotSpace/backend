# type: ignore
import logging
from rest_framework.views import APIView
from rest_framework import status

from core.apps.api.exceptions.wabhook import WebhookConnectionError, WebhookInvalidStatusCode
from core.apps.api.models.project import ProjectModel
from core.apps.api.services.webhook import service_send_webhook
from core.services.response import error_response, success_response
from rest_framework.permissions import AllowAny


class BotWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, method, uuid):
        if method not in ["debug", "release"]:
            return error_response({"method": ["invalid method"]}, status.HTTP_400_BAD_REQUEST)
        if uuid is None or uuid == "" or str(uuid).strip(" ") == "":
            return error_response({"uuid": "invlaid uuid"})
        instance = ProjectModel.objects.none()
        service_name = ""
        try:
            if method == "release":
                instance = ProjectModel.objects.get(release_webhook_uuid=uuid)
                service_name = "release_%s_%s" % (instance.pk, instance.release.version)
            else:
                instance = ProjectModel.objects.get(debug_webhook_uuid=uuid)
                service_name = "debug_%s" % instance.pk
        except ProjectModel.DoesNotExist:
            return error_response({"detail": "Project does not exists"}, status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error("webhook error=%s", e)
            return error_response({"detail": "internal server error"})
        try:
            service_send_webhook(service_name, request.data)
        except (WebhookConnectionError, WebhookInvalidStatusCode) as e:
            return error_response({"detail": str(e)})
        return success_response({"detail": "ok"})
