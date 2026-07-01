import logging

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.api.models.managed_bot import ManagedBotModel
from core.apps.api.services.managed_bot import fetch_managed_bot_token
from core.apps.credentials.services import crypto

logger = logging.getLogger(__name__)


class ManagedBotWebhookView(APIView):
    """POST /api/managed-bot/webhook/<secret>/ — Telegram manager bot updates."""

    permission_classes = []
    authentication_classes = []

    def post(self, request, secret):
        expected = getattr(settings, "MANAGER_BOT_WEBHOOK_SECRET", "")
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not expected or secret != expected or header_secret != expected:
            return Response(status=403)

        body = request.data
        managed_bot = body.get("managed_bot")
        if not managed_bot:
            return Response(status=200)

        bot = managed_bot.get("bot", {})
        creator = managed_bot.get("user", {})
        bot_id = bot.get("id")
        creator_id = creator.get("id")

        if not bot_id:
            logger.warning("managed_bot update'da bot.id yo'q")
            return Response(status=200)

        token = fetch_managed_bot_token(bot_id)
        if not token:
            logger.error("Bot %s uchun token olinmadi", bot_id)
            return Response(status=200)

        from django.contrib.auth import get_user_model
        from django.core.cache import cache

        User = get_user_model()
        owner = None
        username = (bot.get("username") or "").lower()

        # 1) Wizard claim (username bo'yicha) — botni YARATGAN SESSIYA egasiga bog'la.
        #    Telegram-yaratuvchi boshqa akkaunt bo'lishi mumkin, shuning uchun claim ustuvor.
        if username:
            claimed_id = cache.get(f"managed_bot_claim:{username}")
            if claimed_id:
                owner = User.objects.filter(id=claimed_id).first()
                cache.delete(f"managed_bot_claim:{username}")

        # 2) Fallback: yaratuvchi Telegram akkaunti -> BotUser -> phone -> User
        if owner is None and creator_id:
            from core.apps.authbot.models.user import BotUser

            bot_user = BotUser.objects.filter(user_id=creator_id).first()
            if bot_user:
                owner = User.objects.filter(phone=bot_user.phone).first()

        if owner is None:
            logger.warning("managed_bot: owner topilmadi bot=@%s creator=%s", username, creator_id)

        token_encrypted = crypto.encrypt({"token": token})
        ManagedBotModel.objects.update_or_create(
            tg_bot_id=bot_id,
            defaults={
                "owner": owner,
                "username": bot.get("username") or "",
                "name": bot.get("first_name") or "",
                "token_encrypted": token_encrypted,
            },
        )
        return Response(status=200)


class ManagedBotListView(APIView):
    """GET /api/managed-bot/ — auth user'ning managed botlari."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        bots = ManagedBotModel.objects.filter(owner=request.user).order_by("-id")
        data = [
            {
                "id": b.id,
                "tg_bot_id": b.tg_bot_id,
                "username": b.username,
                "name": b.name,
                "created_at": b.created_at,
                "used": b.used,
            }
            for b in bots
        ]
        return Response(data)


class ManagedBotConfigView(APIView):
    """GET /api/managed-bot/config/ — wizard uchun deep-link template."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        manager_username = getattr(settings, "MANAGER_BOT_USERNAME", "")
        manager_token = getattr(settings, "MANAGER_BOT_TOKEN", "")
        if not manager_token or not manager_username:
            return Response({"enabled": False})
        return Response(
            {
                "enabled": True,
                "manager_username": manager_username,
                "deep_link_template": f"https://t.me/newbot/{manager_username}/{{username}}?name={{name}}",
            }
        )


class ManagedBotClaimView(APIView):
    """POST /api/managed-bot/claim/ {username} — wizard bot yaratishdan OLDIN claim qo'yadi.

    Shu tufayli webhook kelganda bot Telegram-yaratuvchiga emas, wizard'da login
    qilgan foydalanuvchiga bog'lanadi (username bo'yicha, 15 daqiqa TTL).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.core.cache import cache

        username = (request.data.get("username") or "").strip().lower()
        if not username:
            return Response({"detail": "username majburiy"}, status=400)
        cache.set(f"managed_bot_claim:{username}", request.user.id, 900)
        return Response({"ok": True})
