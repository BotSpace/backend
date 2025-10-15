import logging
from unittest.mock import patch, MagicMock
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.cms.models import CollectionModel
from model_bakery import baker


@pytest.fixture
def instance(db):
    return baker.make(CollectionModel, name="test")


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
            "query": reverse("collection-query", kwargs={"pk": instance.pk}),
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


@pytest.mark.django_db
def test_insert(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.insert_one") as mock_insert:
        mock_insert.return_value = "mock_id"
        response = client.post(
            urls["query"] + "?action=insert",
            data={
                "name": "Samandar",
            },
        )
        data = response.json()
        assert data["status"] is True
        assert data["data"]["inserted_id"] == "mock_id"
        assert response.status_code == 200


@pytest.mark.django_db
def test_find(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.find") as mock_find:
        mock_find.return_value = [{"name": "Samandar"}]
        response = client.post(
            urls["query"] + "?action=find",
            data={
                "where": {"name": "Samandar"},
            },
            format="json",
        )
        data = response.json()
        assert data["status"] is True
        assert data["data"][0]["name"] == "Samandar"
        assert response.status_code == 200


@pytest.mark.django_db
def test_find_one(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.find_one") as mock_find:
        mock_find.return_value = {"name": "Samandar"}
        response = client.post(
            urls["query"] + "?action=find_one",
            data={
                "where": {"name": "Samandar"},
            },
            format="json",
        )
        data = response.json()
        assert data["status"] is True
        assert data["data"]["name"] == "Samandar"
        assert response.status_code == 200


@pytest.mark.django_db
def test_find_one_invalid(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.find_one") as mock_find:
        mock_find.return_value = None
        response = client.post(
            urls["query"] + "?action=find_one",
            data={
                "where": {"name": "Samandar"},
            },
            format="json",
        )
        data = response.json()
        assert data["status"] is False
        assert response.status_code == 404


@pytest.mark.django_db
def test_update_data(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.update") as mock_find:
        mock = MagicMock()
        mock.modified_count = 10
        mock_find.return_value = mock
        response = client.post(
            urls["query"] + "?action=update",
            data={
                "where": {"name": "Samandar"},
                "data": {"$set": {"name": "Muhiddin ko't"}},
            },
            format="json",
        )
        data = response.json()
        assert data["status"] is True
        assert data["data"]["modified_count"] == 10
        assert response.status_code == 200


@pytest.mark.django_db
def test_delete(data):
    urls, client, _ = data
    with patch("core.apps.cms.views.cms.delete") as mock_find:
        mock = MagicMock()
        mock.deleted_count = 10
        mock_find.return_value = mock
        response = client.post(
            urls["query"] + "?action=delete",
            data={
                "where": {"name": "Samandar"},
            },
            format="json",
        )
        data = response.json()
        assert data["status"] is True
        assert data["data"]["deleted_count"] == 10
        assert response.status_code == 200
