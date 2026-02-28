"""
All urls configurations tree
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.env import env
from core.apps.api.views.docker import logs


def home(request):
    return HttpResponse("OK: #1.0.14-prod")


urlpatterns = [
    path("health/", home),
    path("authbot/", include("core.apps.authbot.urls")),
    path("", include("core.apps.accounts.urls")),
    path("api/", include("core.apps.shared.urls")),
    path("api/", include("core.apps.api.urls")),
    path("sse/api/project/<str:service_id>/logs/", logs),
    path("api/", include("core.apps.cms.urls")),
    path("", include("django_prometheus.urls")),
    path("api/", include("core.apps.payment.urls")),
    path("api/", include("core.apps.template.urls")),
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
