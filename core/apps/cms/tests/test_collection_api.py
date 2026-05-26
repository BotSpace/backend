import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.cms.models import Collection, Field


@pytest.fixture
def cms_client(db):
    project = ProjectModel._create_fake()
    client = APIClient()
    client.force_authenticate(project.owner)
    return client, project


@pytest.mark.django_db
def test_create_collection_is_idempotent_for_existing_name(cms_client):
    client, project = cms_client
    url = f"/api/cms/projects/{project.id}/collections/"

    payload = {
        "name": "students",
        "label": "Talabalar",
        "description": "O'quv markaz talabalari",
        "fields": [
            {"name": "full_name", "kind": "text", "label": "To'liq ism", "required": True},
            {"name": "phone", "kind": "phone", "label": "Telefon raqam", "required": True},
        ],
    }

    first = client.post(url, payload, format="json")
    second = client.post(url, payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    assert Collection.objects.filter(project=project, name="students", deleted_at__isnull=True).count() == 1
    assert Field.objects.filter(collection__project=project, collection__name="students").count() == 2


@pytest.mark.django_db
def test_create_collection_updates_missing_fields_when_existing(cms_client):
    client, project = cms_client
    collection = Collection.objects.create(project=project, owner=project.owner, name="students", label="Old")
    Field.objects.create(collection=collection, name="full_name", kind="text", label="Old name")

    response = client.post(
        f"/api/cms/projects/{project.id}/collections/",
        {
            "name": "students",
            "label": "Talabalar",
            "fields": [
                {"name": "full_name", "kind": "text", "label": "To'liq ism", "required": True},
                {"name": "phone", "kind": "phone", "label": "Telefon raqam", "required": True},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    collection.refresh_from_db()
    assert collection.label == "Talabalar"
    assert list(collection.fields.order_by("name").values_list("name", "label", "required")) == [
        ("full_name", "To'liq ism", True),
        ("phone", "Telefon raqam", True),
    ]
