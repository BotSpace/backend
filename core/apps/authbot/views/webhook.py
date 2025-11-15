from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from telebot import types
from ..management.commands.base import bot
from .. import handlers
import logging

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(APIView):
    """
    Telegram webhook view to handle incoming updates
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            if bot is None:
                logger.error("Bot is not initialized")
                return Response({"error": "Bot not initialized"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            json_string = request.body.decode('utf-8')
            update = types.Update.de_json(json_string)
            
            # Process the update
            bot.process_new_updates([update])
            
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
