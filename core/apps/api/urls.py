from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import BotView, FlowView, ProjectView, RelaseView

router = DefaultRouter()
router.register("relase", RelaseView, basename="relase")
router.register("flow", FlowView, basename="flow")
router.register("bot", BotView, basename="bot")
router.register("project", ProjectView, basename="project")
urlpatterns = [path("", include(router.urls))]
