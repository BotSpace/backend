"""Accounts app URLs.

The module is mount-point-agnostic so it can be included under
``/api/v1/`` and legacy ``/`` aliases in ``config.urls``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt import views as jwt_views

from .views import (
    APITokenViewSet,
    BalanceView,
    ChangePasswordView,
    CustomTokenObtainPairView,
    MeView,
    OAuthAuthorizeApproveView,
    OAuthAuthorizeMetaView,
    OAuthRegisterView,
    OAuthTokenView,
    RegisterView,
    ResetPasswordView,
    TokenExchangeView,
    VerificationView,
)

router = DefaultRouter()
router.register("auth", RegisterView, basename="auth")
router.register("auth", ResetPasswordView, basename="reset-password")
router.register("auth", MeView, basename="me")
router.register("auth", ChangePasswordView, basename="change-password")
router.register("kyc", VerificationView, basename="kyc")


urlpatterns = [
    path("", include(router.urls)),
    path("user/balance/", BalanceView.as_view({"get": "get_balance"}), name="get-balance"),
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/verify/", jwt_views.TokenVerifyView.as_view(), name="token_verify"),
    path("auth/token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "auth/api-tokens/",
        APITokenViewSet.as_view({"get": "list", "post": "create"}),
        name="api-tokens",
    ),
    path(
        "auth/api-tokens/<int:pk>/",
        APITokenViewSet.as_view({"delete": "destroy"}),
        name="api-tokens-detail",
    ),
    path(
        "auth/token/exchange/",
        TokenExchangeView.as_view({"post": "create"}),
        name="token-exchange",
    ),
    # OAuth 2.1 endpoints
    path("auth/oauth/register/", OAuthRegisterView.as_view(), name="oauth-register"),
    path("auth/oauth/authorize/meta/", OAuthAuthorizeMetaView.as_view(), name="oauth-authorize-meta"),
    path("auth/oauth/authorize/approve/", OAuthAuthorizeApproveView.as_view(), name="oauth-authorize-approve"),
    path("auth/oauth/token/", OAuthTokenView.as_view(), name="oauth-token"),
]
