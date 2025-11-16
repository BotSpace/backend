from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.template.views.template import TemplateCategoryView, TemplateFeatureView

from .views import TemplateOrderView, TemplateView, UsertemplateView

router = DefaultRouter()
router.register("order", TemplateOrderView, basename="order")
router.register("my-template", UsertemplateView, basename="usertemplate")
router.register("template", TemplateView, basename="template")
router.register("category", TemplateCategoryView, basename="category")
router.register("feature", TemplateFeatureView, basename="feature")
urlpatterns = [path("", include(router.urls))]
