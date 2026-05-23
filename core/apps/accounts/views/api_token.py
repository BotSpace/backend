import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from core.apps.accounts.models.api_token import PersonalAccessToken
from core.services.response import error_response, success_response

logger = logging.getLogger(__name__)


class APITokenViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET /auth/api-tokens/ — foydalanuvchi tokenlar ro'yxati"""
        tokens = PersonalAccessToken.objects.filter(user=request.user).values(
            "id", "name", "prefix", "last_used_at", "created_at",
        )
        return success_response(list(tokens))

    def create(self, request):
        """POST /auth/api-tokens/ — yangi API token yaratish"""
        name = (request.data.get("name") or "API Token").strip()
        if not name:
            return error_response({"name": "Token nomi kerak"}, 400)

        count = PersonalAccessToken.objects.filter(user=request.user).count()
        if count >= 10:
            return error_response({"detail": "Maksimum 10 ta token yaratish mumkin"}, 400)

        pat, raw_token = PersonalAccessToken.create_token(request.user, name)
        logger.info("API token created: user_id=%s name=%r", request.user.id, name)
        return Response(
            {"status": True, "data": {"id": pat.id, "name": name, "token": raw_token, "prefix": pat.prefix}},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        """DELETE /auth/api-tokens/{id}/ — tokenni o'chirish"""
        try:
            pat = PersonalAccessToken.objects.get(id=pk, user=request.user)
        except PersonalAccessToken.DoesNotExist:
            return error_response({"detail": "Token topilmadi"}, 404)
        pat.delete()
        return success_response({"deleted": True})


class TokenExchangeView(ViewSet):
    """POST /auth/token/exchange/ — API token → JWT access+refresh"""
    permission_classes = [AllowAny]

    def create(self, request):
        raw_token = request.data.get("token", "").strip()
        if not raw_token:
            return error_response({"detail": "token maydoni kerak"}, 400)

        pat = PersonalAccessToken.verify(raw_token)
        if pat is None:
            return error_response({"detail": "Noto'g'ri yoki o'chirilgan token"}, 401)

        refresh = RefreshToken.for_user(pat.user)
        return success_response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
