from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BotView, ProjectView, RelaseView

router = DefaultRouter()
router.register("relase", RelaseView, basename="relase")
router.register("bot", BotView, basename="bot")
router.register("project", ProjectView, basename="project")
urlpatterns = [path("", include(router.urls))]
