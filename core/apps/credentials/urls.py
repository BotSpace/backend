from __future__ import annotations

from django.urls import path

from core.apps.credentials.views import CredentialTypeViewSet, CredentialViewSet

# CredentialType endpoints
type_list = CredentialTypeViewSet.as_view({"get": "list", "post": "create"})
type_detail = CredentialTypeViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy"}
)

# Credential endpoints
cred_list = CredentialViewSet.as_view({"get": "list", "post": "create"})
cred_detail = CredentialViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
cred_test = CredentialViewSet.as_view({"post": "test_credential"})

urlpatterns = [
    # Types (global — not project-scoped)
    path("credentials/types/", type_list, name="credential-type-list"),
    path("credentials/types/<slug:key>/", type_detail, name="credential-type-detail"),

    # Project-scoped credentials
    path(
        "credentials/projects/<str:project_id>/credentials/",
        cred_list,
        name="credential-list",
    ),
    path(
        "credentials/projects/<str:project_id>/credentials/<int:pk>/",
        cred_detail,
        name="credential-detail",
    ),
    path(
        "credentials/projects/<str:project_id>/credentials/<int:pk>/test/",
        cred_test,
        name="credential-test",
    ),
]
