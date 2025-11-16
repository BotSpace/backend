from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TemplateOrderView, TemplateView, UsertemplateView

router = DefaultRouter()
router.register("order", TemplateOrderView, basename="order")
router.register("me-template", UsertemplateView, basename="usertemplate")
router.register("template", TemplateView, basename="template")
urlpatterns = [path("", include(router.urls))]
