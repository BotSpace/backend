from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.api.services.overview import OverviewService


class OverviewView(APIView):
    """Dashboard aggregate overview for the authenticated user.

    GET /api/v1/dashboard/overview/
    Legacy alias: GET /api/dashboard/overview/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        data = OverviewService(request.user).get()
        return Response(data)
