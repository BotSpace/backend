from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.api.views.webhook import BotWebhookView


from .views import EnviromentView, ProjectView, ReleaseView, MessageView

router = DefaultRouter()
router.register("enviroment", EnviromentView, basename="enviroment")
router.register("relase", ReleaseView, basename="relase")
router.register("project", ProjectView, basename="project")
router.register("message", MessageView, basename="message")
urlpatterns = [
    path("", include(router.urls)),
    path("bot-webhook/<str:method>/<str:uuid>/", BotWebhookView.as_view(), name="bot-webhook"),
]
