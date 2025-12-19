import logging
from rest_framework.views import APIView
from ..serializers import LoginSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from core.apps.accounts.models import User
from core.services import UserService
from core.apps.accounts.serializers import UserSerializer
from ..management.commands.base import bot
from datetime import datetime


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        code = ser.validated_data.get("code")
        user = code.user
        user, _ = User.objects.get_or_create(
            phone=user.phone,
            defaults={
                "phone": user.phone,
                "first_name": user.first_name if user.first_name is not None else "",
                "last_name": user.last_name if user.last_name is not None else "",
            },
        )
        service = UserService()
        token = service.validate_user(user)
        try:
            bot.edit_message_text(
                chat_id=code.user.user_id,
                message_id=code.message_id,
                text="Tasdiqlash ko'di foydalanildi 🫡 ```{}```".format(datetime.now().strftime("%d-%m-%Y %H:%M:%S")),
                parse_mode="markdown",
            )
        except Exception as err:
            logging.error(err)
        code.delete()
        return Response(
            {"user": UserSerializer(user).data, "token": token},
            status=status.HTTP_200_OK,
        )
