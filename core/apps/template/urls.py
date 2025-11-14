from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TemplateView, UsertemplateView

router = DefaultRouter()
router.register("usertemplate", UsertemplateView, basename="usertemplate")
router.register("template", TemplateView, basename="template")
urlpatterns = [path("", include(router.urls))]
