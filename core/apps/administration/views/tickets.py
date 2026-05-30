# type: ignore
"""Support tickets — placeholder until the `tickets` app/models exist.

Current state: project doesn't have a Ticket model. This view returns
an empty list so the admin UI renders gracefully; the frontend's
Tickets page will show a "tizim hali to'liq sozlanmagan" notice.
"""

from rest_framework import viewsets
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser


class AdminTicketsView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        return Response({"results": [], "count": 0, "detail": "Ticket model not implemented yet."})

    def retrieve(self, request, pk=None):
        return Response({"detail": "Ticket model not implemented yet."}, status=404)
