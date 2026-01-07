from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.template.views.template import TemplateCategoryView, TemplateFeatureView
from core.apps.template.views.submission import TemplateSubmissionView

from .views import TemplateOrderView, TemplateView

router = DefaultRouter()
router.register("order", TemplateOrderView, basename="order")
# router.register("my-template", UsertemplateView, basename="usertemplate")
router.register("list", TemplateView, basename="template")
router.register("category", TemplateCategoryView, basename="category")
router.register("feature", TemplateFeatureView, basename="feature")
router.register("submission", TemplateSubmissionView, basename="submission")
urlpatterns = [path("template/", include(router.urls))]
