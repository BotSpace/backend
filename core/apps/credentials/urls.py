from __future__ import annotations

from django.urls import path

from core.apps.credentials.views import CredentialTypeListView, CredentialViewSet

cred_list = CredentialViewSet.as_view({"get": "list", "post": "create"})
cred_detail = CredentialViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
cred_test = CredentialViewSet.as_view({"post": "test_credential"})

urlpatterns = [
    # Registry — read-only
    path("credentials/types/", CredentialTypeListView.as_view(), name="credential-type-list"),
    # Owner-scoped credentials
    path("credentials/", cred_list, name="credential-list"),
    path("credentials/<int:pk>/", cred_detail, name="credential-detail"),
    path("credentials/<int:pk>/test/", cred_test, name="credential-test"),
]
