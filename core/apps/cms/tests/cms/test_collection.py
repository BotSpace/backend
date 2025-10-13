import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.cms.models import CollectionModel


@pytest.fixture
def instance(db):
    return CollectionModel._create_fake()


@pytest.fixture
def api_client(instance):
    client = APIClient()
    client.force_authenticate(user=instance.user)
    return client, instance


@pytest.fixture
def data(api_client):
    client, instance = api_client
    return (
        {
            "list": reverse("collection-list"),
            "retrieve": reverse("collection-detail", kwargs={"pk": instance.pk}),
            "retrieve-not-found": reverse("collection-detail", kwargs={"pk": 1000}),
        },
        client,
        instance,
    )


@pytest.mark.django_db
def test_create(data):
    urls, client, _ = data
    response = client.post(urls["list"], data={"name": "test"})
    assert response.json()["status"] is True
    assert response.status_code == 201


def test_update(data):
    urls, client, _ = data
    response = client.patch(
        urls["retrieve"],
        data={
            "name": "updated",
        },
    )
    assert response.json()["status"] is True
    assert response.status_code == 200
    response = client.get(urls["retrieve"])
    assert response.json()["status"] is True
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "updated"


def test_partial_update():
    assert True


def test_destroy():
    assert True


@pytest.mark.django_db
def test_list(data):
    urls, client, _ = data
    response = client.get(urls["list"])
    data = response.json()
    assert response.status_code == 200
    assert data["status"] is True


@pytest.mark.django_db
def test_retrieve(data):
    urls, client, _ = data
    response = client.get(urls["retrieve"])
    data = response.json()
    assert response.status_code == 200
    assert data["status"] is True


@pytest.mark.django_db
def test_retrieve_not_found(data):
    urls, client, _ = data
    response = client.get(urls["retrieve-not-found"])
    data = response.json()
    assert response.status_code == 404
    assert data["status"] is False
