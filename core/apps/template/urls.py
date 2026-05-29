from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.template.views.template import TemplateCategoryView, TemplateFeatureView
from core.apps.template.views.submission import TemplateSubmissionView
from core.apps.template.views.withdrawal import TemplateWithdrawalView
from core.apps.template.views.internal import (
    list_templates_with_flow,
    get_template_with_flow,
)

from .views import TemplateOrderView, TemplateView

router = DefaultRouter()
router.register("order", TemplateOrderView, basename="order")
# router.register("my-template", UsertemplateView, basename="usertemplate")
router.register("list", TemplateView, basename="template")
router.register("category", TemplateCategoryView, basename="category")
router.register("feature", TemplateFeatureView, basename="feature")
router.register("submission", TemplateSubmissionView, basename="submission")
router.register("withdrawal", TemplateWithdrawalView, basename="withdrawal")
urlpatterns = [
    path("template/internal/list/", list_templates_with_flow),
    path("template/internal/<str:identifier>/", get_template_with_flow),
    path("template/", include(router.urls)),
]
