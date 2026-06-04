"""cms create javobida `id` qaytishi (relation qurish uchun, feedback #6)."""

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_create_collection_response_includes_id():
    user = baker.make("accounts.User")
    project = baker.make("api.ProjectModel", owner=user)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        f"/cms/projects/{project.pk}/collections/",
        {"name": "movies", "label": "Kinolar", "fields": [{"name": "title", "kind": "text"}]},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.content
    assert resp.data.get("id") is not None
