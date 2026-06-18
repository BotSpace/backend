from __future__ import annotations

from django.urls import path

from core.apps.credentials.views import (
    CredentialOptionsView,
    CredentialTypeListView,
    CredentialViewSet,
    OAuthCallbackView,
    OAuthStartView,
)

cred_list = CredentialViewSet.as_view({"get": "list", "post": "create"})
cred_detail = CredentialViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
cred_test = CredentialViewSet.as_view({"post": "test_credential"})
cred_reveal = CredentialViewSet.as_view({"get": "reveal"})

urlpatterns = [
    # Registry — read-only
    path("credentials/types/", CredentialTypeListView.as_view(), name="credential-type-list"),
    # Owner-scoped credentials
    path("credentials/", cred_list, name="credential-list"),
    path("credentials/<int:pk>/", cred_detail, name="credential-detail"),
    path("credentials/<int:pk>/test/", cred_test, name="credential-test"),
    path("credentials/<int:pk>/reveal/", cred_reveal, name="credential-reveal"),
    # Dynamic options (load-options)
    path("credentials/options/<str:resource>/", CredentialOptionsView.as_view(), name="credential-options"),
    # OAuth2 flow
    path("credentials/oauth/<str:provider>/start/", OAuthStartView.as_view(), name="credential-oauth-start"),
    path("credentials/oauth/<str:provider>/callback/", OAuthCallbackView.as_view(), name="credential-oauth-callback"),
]
