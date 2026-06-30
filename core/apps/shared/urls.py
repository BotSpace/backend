from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConfigViewSet, SettingsView
from .views.manifest import builtin_node_manifests_view

router = DefaultRouter()
router.register("settings", SettingsView, basename="settings")
# Config: admin CRUD (list + PATCH /{key}/) and public read (/public/)
router.register("shared/config", ConfigViewSet, basename="config")

urlpatterns = [
    path("shared/manifest/builtin-nodes/", builtin_node_manifests_view, name="builtin-node-manifests"),
    path("", include(router.urls)),
]
