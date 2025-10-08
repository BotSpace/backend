from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BotView, EnviromentView, ProjectView, RelaseView

router = DefaultRouter()
router.register("enviroment", EnviromentView, basename="enviroment")
router.register("relase", RelaseView, basename="relase")
router.register("bot", BotView, basename="bot")
router.register("project", ProjectView, basename="project")
urlpatterns = [path("", include(router.urls))]
