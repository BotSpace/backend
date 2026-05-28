import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import EnviromentModel


@pytest.fixture
def env_client(db):
    instance = EnviromentModel._create_fake()
    client = APIClient()
    client.force_authenticate(instance.project.owner)
    urls = {
        "list": reverse("enviroment-list") + f"?project={instance.project.pk}",
        "retrieve": reverse("enviroment-detail", kwargs={"pk": instance.key}) + f"?project={instance.project.id}",
        "retrieve-not-found": reverse("enviroment-detail", kwargs={"pk": "NO_KEY"}) + f"?project={instance.project.id}",
    }
    return client, urls, instance


@pytest.mark.django_db
def test_env_create(env_client):
    client, urls, instance = env_client
    response = client.post(
        urls["list"],
        data={"key": "test", "value": "test", "project": instance.project.pk},
    )
    assert response.status_code == 201
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_env_create_upserts_on_duplicate_key(env_client):
    """POST with the same (project, key) must update the value, not 400."""
    client, urls, instance = env_client
    response = client.post(
        urls["list"],
        data={"key": instance.key, "value": "new-value", "project": instance.project.pk},
    )
    assert response.status_code == 201, response.json()
    assert response.json()["status"] is True
    instance.refresh_from_db()
    assert instance.value == "new-value"


@pytest.mark.django_db
def test_env_update(env_client):
    client, urls, _ = env_client
    response = client.patch(urls["retrieve"], data={"flow": [{"step": "init", "action": "initialize release"}]})
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_env_partial_update(env_client):
    # Bu test shunchaki mavjudligi uchun qolgan
    assert True


@pytest.mark.django_db
def test_env_destroy(env_client):
    client, urls, _ = env_client
    response = client.delete(urls["retrieve"])
    assert response.status_code == 204


@pytest.mark.django_db
def test_env_list(env_client):
    client, urls, _ = env_client
    response = client.get(urls["list"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_env_retrieve(env_client):
    client, urls, _ = env_client
    response = client.get(urls["retrieve"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_env_retrieve_not_found(env_client):
    client, urls, _ = env_client
    response = client.get(urls["retrieve-not-found"])
    assert response.status_code == 404
    assert response.json()["status"] is False
