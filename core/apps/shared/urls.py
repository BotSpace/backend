from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConfigViewSet, SettingsView

router = DefaultRouter()
router.register("settings", SettingsView, basename="settings")
# Config: admin CRUD (list + PATCH /{key}/) and public read (/public/)
router.register("shared/config", ConfigViewSet, basename="config")

urlpatterns = [
    path("", include(router.urls)),
]
