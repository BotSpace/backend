"""
All urls configurations tree
"""

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.env import env
from core.apps.api.views.docker import logs


def home(request):
    return HttpResponse("OK: #22f1d7ceaecce53c8c2d91872c92e31ce7220e60")


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
if env.str("PROJECT_ENV") == "debug":
    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
urlpatterns += [
    re_path("static/(?P<path>.*)", serve, {"document_root": settings.STATIC_ROOT}),
    re_path("media/(?P<path>.*)", serve, {"document_root": settings.MEDIA_ROOT}),
]
