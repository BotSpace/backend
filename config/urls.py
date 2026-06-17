"""All URL configurations.

API surface is exposed under ``/api/v1/``. Legacy paths (``/api/…``,
``/auth/…``, etc.) are kept as aliases pointing to the same view set so
existing clients continue to work; new code should target ``/api/v1/``.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.env import env
from core.apps.accounts.views import BalanceView, OAuthMetadataView
from core.apps.api.views.docker import logs
from core.apps.shared.views.health import liveness, readiness


def home(request):
    return HttpResponse("OK: #1.0.14-prod")


api_v1_patterns = [
    path("", include("core.apps.accounts.urls")),
    path("", include("core.apps.shared.urls")),
    path("", include("core.apps.api.urls")),
    path("", include("core.apps.cms_legacy.urls")),
    path("", include("core.apps.cms.urls")),
    path("", include("core.apps.credentials.urls")),
    path("", include("core.apps.payment.urls")),
    path("", include("core.apps.template.urls")),
    path("", include("core.apps.administration.urls")),
    path("", include("core.apps.tickets.urls")),
    path("", include("core.apps.blog.urls")),
]


urlpatterns = [
    # RFC 8414 metadata — must live at the root (not under /api/v1/)
    path(".well-known/oauth-authorization-server", OAuthMetadataView.as_view(), name="oauth-metadata"),
    path("health/", home, name="health"),
    path("healthz/", liveness, name="liveness"),
    path("readyz/", readiness, name="readiness"),
    path("authbot/", include("core.apps.authbot.urls")),
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    path("sse/api/v1/project/<str:service_id>/logs/", logs, name="project-logs"),
    path("", include("django_prometheus.urls")),
    # ---- Legacy aliases (DEPRECATED). Clients should migrate to /api/v1/. ----
    path("", include("core.apps.accounts.urls")),
    path("api/", include("core.apps.shared.urls")),
    path("api/", include("core.apps.api.urls")),
    path("api/", include("core.apps.cms_legacy.urls")),
    path("api/", include("core.apps.cms.urls")),
    path("api/", include("core.apps.credentials.urls")),
    path("api/", include("core.apps.payment.urls")),
    path("api/", include("core.apps.template.urls")),
    path("api/", include("core.apps.administration.urls")),
    path("api/", include("core.apps.tickets.urls")),
    path("api/", include("core.apps.blog.urls")),
    # Old custom paths preserved verbatim
    path("api/user/balance/", BalanceView.as_view({"get": "get_balance"}), name="legacy-get-balance"),
    path("sse/api/project/<str:service_id>/logs/", logs, name="legacy-project-logs"),
]
urlpatterns += [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("rosetta/", include("rosetta.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls"), name="ck_editor_5_upload_file"),
]
if env.bool("SILK_ENABLED", False):
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

urlpatterns += [
    path(
        "schema/",
        staff_member_required(SpectacularAPIView.as_view(), login_url="/admin/login/"),
        name="schema",
    ),
    path(
        "swagger/",
        staff_member_required(SpectacularSwaggerView.as_view(url_name="schema"), login_url="/admin/login/"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        staff_member_required(SpectacularRedocView.as_view(url_name="schema"), login_url="/admin/login/"),
        name="redoc",
    ),
]

urlpatterns += [
    re_path("static/(?P<path>.*)", serve, {"document_root": settings.STATIC_ROOT}),
    re_path("media/(?P<path>.*)", serve, {"document_root": settings.MEDIA_ROOT}),
]
