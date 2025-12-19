from .views import LoginView, TelegramWebhookView
from django.urls import path


app_name = "authbot"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("webhook/", TelegramWebhookView.as_view(), name="webhook"),
]
