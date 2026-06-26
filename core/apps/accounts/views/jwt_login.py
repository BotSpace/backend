import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """TokenObtainPairView that records every successful JWT login."""

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        try:
            from core.apps.accounts.services import record_login

            record_login(serializer.user, "jwt")
        except Exception:
            logger.exception("record_login failed for jwt")

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
