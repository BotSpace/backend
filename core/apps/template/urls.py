from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TemplateView

router = DefaultRouter()
router.register("template", TemplateView, basename="template")
urlpatterns = [path("", include(router.urls))]
