from __future__ import annotations

from django.urls import path

from core.apps.cms.views import (
    CollectionAuditView,
    CollectionViewSet,
    DocumentViewSet,
    WebhookViewSet,
)


# CollectionViewSet
collection_list = CollectionViewSet.as_view({"get": "list", "post": "create"})
collection_detail = CollectionViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy"}
)
collection_add_field = CollectionViewSet.as_view({"post": "add_field"})
collection_field_detail = CollectionViewSet.as_view(
    {"patch": "update_field", "delete": "remove_field"}
)

# DocumentViewSet
doc_list = DocumentViewSet.as_view({"get": "list", "post": "create"})
doc_detail = DocumentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
doc_bulk = DocumentViewSet.as_view({"post": "bulk_insert"})
doc_aggregate = DocumentViewSet.as_view({"post": "aggregate"})
doc_count = DocumentViewSet.as_view({"get": "count"})
doc_restore = DocumentViewSet.as_view({"post": "restore"})


# Webhooks
webhook_list = WebhookViewSet.as_view({"get": "list", "post": "create"})
webhook_detail = WebhookViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)


urlpatterns = [
    # Collections
    path("cms/projects/<str:project_id>/collections/", collection_list,
         name="cms-coll-list"),
    path("cms/projects/<str:project_id>/collections/<slug:name>/", collection_detail,
         name="cms-coll-detail"),
    path("cms/projects/<str:project_id>/collections/<slug:name>/fields/",
         collection_add_field, name="cms-coll-add-field"),
    path("cms/projects/<str:project_id>/collections/<slug:name>/fields/<slug:field_name>/",
         collection_field_detail, name="cms-coll-field-detail"),

    # Documents
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/",
         doc_list, name="cms-doc-list"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/bulk/",
         doc_bulk, name="cms-doc-bulk"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/aggregate/",
         doc_aggregate, name="cms-doc-aggregate"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/count/",
         doc_count, name="cms-doc-count"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/<str:pk>/",
         doc_detail, name="cms-doc-detail"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/documents/<str:pk>/restore/",
         doc_restore, name="cms-doc-restore"),

    # Audit
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/audit/",
         CollectionAuditView.as_view(), name="cms-coll-audit"),

    # Webhooks
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/webhooks/",
         webhook_list, name="cms-webhook-list"),
    path("cms/projects/<str:project_id>/collections/<slug:collection_name>/webhooks/<int:pk>/",
         webhook_detail, name="cms-webhook-detail"),
]
