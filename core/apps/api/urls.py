from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from core.apps.api.views.resource import UsedView
from core.apps.api.views.webhook import BotWebhookView

from .views import EnviromentView, FileView, MessageView, ProjectView, ReleaseView, ResourceView

router = DefaultRouter()
router.register("resource", ResourceView, basename="resource")
router.register("file", FileView, basename="file")
router.register("enviroment", EnviromentView, basename="enviroment")
router.register("relase", ReleaseView, basename="relase")
router.register("project", ProjectView, basename="project")
router.register("message", MessageView, basename="message")
urlpatterns = [
    path("", include(router.urls)),
    path("bot-webhook/<str:method>/<str:uuid>/", BotWebhookView.as_view(), name="bot-webhook"),
    re_path(r"^used(?:/(?P<project_id>[0-9]+))?/$", UsedView.as_view(), name="project-used"),
]
