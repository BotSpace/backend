from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from core.apps.api.views.resource import UsedView
from core.apps.api.views.webhook import BotWebhookView
from core.apps.api.views.debug import DebugContextEventView, DebugContextLatestView, DebugNodeEventView
from core.apps.api.views.internal import credential_by_id, project_by_debug_uuid, project_by_release_uuid
from core.apps.api.views.plan import PlanViewSet
from core.apps.api.views.chat import ChatViewSet
from core.apps.api.views.subscription import SubscriptionViewSet
from core.apps.api.views.overview import OverviewView

from .views import EnviromentView, FileView, MessageView, ProjectView, ReleaseView, ResourceView

router = DefaultRouter()
router.register("resource", ResourceView, basename="resource")
router.register("file", FileView, basename="file")
router.register("enviroment", EnviromentView, basename="enviroment")
router.register("relase", ReleaseView, basename="relase")
router.register("project", ProjectView, basename="project")
router.register("message", MessageView, basename="message")
router.register("plans", PlanViewSet, basename="plans")
router.register("chat", ChatViewSet, basename="chat")

urlpatterns = [
    path("", include(router.urls)),
    path("bot-webhook/<str:method>/<str:uuid>/", BotWebhookView.as_view(), name="bot-webhook"),
    re_path(r"^used(?:/(?P<project_id>[0-9a-fA-F-]+))?/$", UsedView.as_view(), name="project-used"),
    # User subscription endpoints
    path(
        "subscription/",
        SubscriptionViewSet.as_view({"get": "current"}),
        name="subscription-current",
    ),
    path(
        "subscription/upgrade/",
        SubscriptionViewSet.as_view({"post": "upgrade"}),
        name="subscription-upgrade",
    ),
    path(
        "subscription/usage/",
        SubscriptionViewSet.as_view({"get": "usage"}),
        name="subscription-usage",
    ),
    path(
        "subscription/usage/report/",
        SubscriptionViewSet.as_view({"post": "report_usage"}),
        name="subscription-usage-report",
    ),
    # Dashboard overview
    path("dashboard/overview/", OverviewView.as_view(), name="dashboard-overview"),
    # Internal endpoints for Golang webhook service
    path("internal/project-by-release-uuid/<uuid:uuid>/", project_by_release_uuid, name="project-by-release-uuid"),
    path("internal/project-by-debug-uuid/<uuid:uuid>/", project_by_debug_uuid, name="project-by-debug-uuid"),
    path("internal/credentials/<int:pk>/", credential_by_id, name="internal-credential-by-id"),
    # Debug node-execution events from engine.
    # Both with/without trailing slash so engines that strip the slash (≤3.5.15)
    # don't hit an APPEND_SLASH 301 → GET → 405.
    path("debug/node-event/", DebugNodeEventView.as_view(), name="debug-node-event"),
    path("debug/node-event", DebugNodeEventView.as_view(), name="debug-node-event-noslash"),
    # Context snapshot: engine POST qiladi → constructor SSE "context" event oladi.
    path("debug/context-event/", DebugContextEventView.as_view(), name="debug-context-event"),
    path("debug/context-event", DebugContextEventView.as_view(), name="debug-context-event-noslash"),
    # Constructor: ulanganda oxirgi snapshot'ni olish (GET ?project_id=&chat_id=).
    path("debug/context/latest/", DebugContextLatestView.as_view(), name="debug-context-latest"),
    path("debug/context/latest", DebugContextLatestView.as_view(), name="debug-context-latest-noslash"),
]
