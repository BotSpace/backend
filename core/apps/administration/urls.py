# type: ignore
"""Admin panel REST API routes.

Mounted under `/api/v1/admin/` (and aliased at `/api/admin/` from
config/urls.py) so the Next.js admin panel can call
`https://api.botspace.uz/api/v1/admin/...`.

Each ViewSet is gated by `core.permissions.engine.IsAdminUser`
(is_staff OR is_superuser).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Views are imported lazily-by-module so each feature file stays small
# and the URL conf reads as a top-level table.
from core.apps.administration.views import (
    audit_log as audit_log_views,
    bot_withdrawals as bot_withdrawals_views,
    kyc as kyc_views,
    orders as orders_views,
    plans as plans_views,
    projects as projects_views,
    settings as settings_views,
    stats as stats_views,
    templates as templates_views,
    tickets as tickets_views,
    transactions as transactions_views,
    users as users_views,
    withdrawals as withdrawals_views,
)


router = DefaultRouter()
router.register("users", users_views.AdminUsersView, basename="admin-users")
router.register("projects", projects_views.AdminProjectsView, basename="admin-projects")
router.register("templates", templates_views.AdminTemplatesView, basename="admin-templates")
router.register(
    "template-submissions",
    templates_views.AdminTemplateSubmissionsView,
    basename="admin-template-submissions",
)
router.register("withdrawals", withdrawals_views.AdminWithdrawalsView, basename="admin-withdrawals")
router.register("bot-withdrawals", bot_withdrawals_views.AdminBotWithdrawalsView, basename="admin-bot-withdrawals")
router.register("kyc-verifications", kyc_views.AdminKycVerificationView, basename="admin-kyc-verifications")
router.register("transactions", transactions_views.AdminTransactionsView, basename="admin-transactions")
router.register("bot-orders", orders_views.AdminBotOrdersView, basename="admin-bot-orders")
router.register("plans", plans_views.AdminPlansView, basename="admin-plans")
router.register("tickets", tickets_views.AdminTicketsView, basename="admin-tickets")
router.register("audit-log", audit_log_views.AdminAuditLogView, basename="admin-audit-log")
router.register("settings", settings_views.AdminSettingsView, basename="admin-settings")


urlpatterns = [
    path("admin/stats/dashboard/", stats_views.dashboard_stats, name="admin-stats-dashboard"),
    path("admin/", include(router.urls)),
]
