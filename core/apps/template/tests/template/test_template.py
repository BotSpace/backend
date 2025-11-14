import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.template.models import TemplateModel


@pytest.fixture
def instance(db):
    return TemplateModel._baker()


@pytest.fixture
def api_client(instance):
    client = APIClient()
    ##client.force_authenticate(user=instance.user)
    return client, instance


@pytest.fixture
def data(api_client):
    client, instance = api_client
    return (
        {
            "list": reverse("template-list"),
            "retrieve": reverse("template-detail", kwargs={"pk": instance.pk}),
            "retrieve-not-found": reverse("template-detail", kwargs={"pk": 1000}),
        },
        client,
        instance,
    )


@pytest.mark.django_db
def test_list(data):
    urls, client, _ = data
    response = client.get(urls["list"])
    data_resp = response.json()
    assert response.status_code == 200
    assert data_resp["status"] is True


@pytest.mark.django_db
def test_retrieve(data):
    urls, client, _ = data
    response = client.get(urls["retrieve"])
    data_resp = response.json()
    assert response.status_code == 200
    assert data_resp["status"] is True


@pytest.mark.django_db
def test_retrieve_not_found(data):
    urls, client, _ = data
    response = client.get(urls["retrieve-not-found"])
    data_resp = response.json()
    assert response.status_code == 404
    assert data_resp["status"] is False


# @pytest.mark.django_db
# def test_create(data):
#    urls, client, _ = data
#    response = client.post(urls["list"], data={"name": "test"})
#    assert response.json()["status"] is True
#    assert response.status_code == 201


# @pytest.mark.django_db
# def test_update(data):
#    urls, client, _ = data
#    response = client.patch(urls["retrieve"], data={"name": "updated"})
#    assert response.json()["status"] is True
#    assert response.status_code == 200
#
#    # verify updated value
#    response = client.get(urls["retrieve"])
#    assert response.json()["status"] is True
#    assert response.status_code == 200
#    assert response.json()["data"]["name"] == "updated"


# @pytest.mark.django_db
# def test_partial_update():
#    urls, client, _ = data
#    response = client.patch(urls["retrieve"], data={"name": "updated"})
#    assert response.json()["status"] is True
#    assert response.status_code == 200
#
#    # verify updated value
#    response = client.get(urls["retrieve"])
#    assert response.json()["status"] is True
#    assert response.status_code == 200
#    assert response.json()["data"]["name"] == "updated"


# @pytest.mark.django_db
# def test_destroy(data):
#    urls, client, _ = data
#    response = client.delete(urls["retrieve"])
#    assert response.status_code == 204
