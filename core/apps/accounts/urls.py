"""Accounts app URLs.

The module is mount-point-agnostic so it can be included under
``/api/v1/`` and legacy ``/`` aliases in ``config.urls``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt import views as jwt_views

from .views import BalanceView, ChangePasswordView, MeView, RegisterView, ResetPasswordView

router = DefaultRouter()
router.register("auth", RegisterView, basename="auth")
router.register("auth", ResetPasswordView, basename="reset-password")
router.register("auth", MeView, basename="me")
router.register("auth", ChangePasswordView, basename="change-password")


urlpatterns = [
    path("", include(router.urls)),
    path("user/balance/", BalanceView.as_view({"get": "get_balance"}), name="get-balance"),
    path("auth/token/", jwt_views.TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/verify/", jwt_views.TokenVerifyView.as_view(), name="token_verify"),
    path("auth/token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
]
