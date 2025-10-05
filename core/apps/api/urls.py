from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import BotView, ProjectView

router = DefaultRouter()
router.register("bot", BotView, basename="bot")
router.register("project", ProjectView, basename="project")
urlpatterns = [path("", include(router.urls))]
