import logging
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel

from core.apps.api.models.project import EnviromentModel
from core.apps.api.services.project import create_default_collections


# --- GLOBAL PATCH FIXTURE ---
@pytest.fixture(autouse=True)
def patch_docker_services():
    with patch("core.apps.api.signals.project.remove_service") as mock_remove, patch(
        "core.apps.api.signals.project.deploy_service"
    ) as mock_deploy, patch("core.apps.api.views.project.deploy_service") as mock_deploy_view, patch(
        "core.apps.api.views.project.set_webhook"
    ) as mock_set_webhook:
        magic = MagicMock()
        magic.metadata.name = "test-deployment-123"
        mock_deploy.return_value = magic
        mock_remove.return_value = True
        mock_deploy_view.return_value = magic
        yield


# --- PLAN FIXTURE ---
@pytest.fixture
def test_plan(db):
    """Create a test plan for projects"""
    plan = PlanModel._create_fake()
    return plan


# --- PROJECT FIXTURE ---
@pytest.fixture
def project_client(db, test_plan):
    instance = ProjectModel._create_fake()
    create_default_collections(instance)
    instance.owner.balance = 1000000
    instance.owner.save()
    client = APIClient()
    client.force_authenticate(instance.owner)
    urls = {
        "list": reverse("project-list"),
        "retrieve": reverse("project-detail", kwargs={"pk": instance.pk}),
        "info": reverse("project-info", kwargs={"pk": instance.pk}),
        "stop": reverse("project-stop", kwargs={"pk": instance.pk}),
        "debug": reverse("project-debug", kwargs={"pk": instance.pk}),
        "retrieve-not-found": reverse("project-detail", kwargs={"pk": 1000}),
    }
    return client, urls, instance, test_plan


# --- PROJECT TESTS ---
@pytest.mark.django_db
def test_project_create(project_client):
    client, urls, _, plan = project_client
    response = client.post(urls["list"], data={"name": "test", "plan_id": plan.id})
    assert response.status_code == 201
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_info(project_client):
    client, urls, _, _ = project_client
    response = client.get(urls["info"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
@patch("core.apps.api.views.project.remove_service")
def test_project_stop(_, project_client):
    client, urls, _, __ = project_client
    response = client.get(urls["stop"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_debug(project_client):
    client, urls, instance, _ = project_client
    EnviromentModel.objects.create(
        project=instance,
        key="BOT_TOKEN",
        value="token",
        user=instance.owner,
    )
    response = client.get(urls["debug"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_update(project_client):
    client, urls, _, plan = project_client
    response = client.put(urls["retrieve"], data={"name": "test", "plan_id": plan.id})
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_partial_update(project_client):
    client, urls, _, __ = project_client
    response = client.patch(urls["retrieve"], data={"name": "test"})
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_destroy(project_client):
    client, urls, _, __ = project_client
    response = client.delete(urls["retrieve"])
    assert response.status_code == 204


@pytest.mark.django_db
def test_project_list(project_client):
    client, urls, _, __ = project_client
    response = client.get(urls["list"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_retrieve(project_client):
    client, urls, _, __ = project_client
    response = client.get(urls["retrieve"])
    assert response.status_code == 200
    assert response.json()["status"] is True


@pytest.mark.django_db
def test_project_retrieve_not_found(project_client):
    client, urls, _, __ = project_client
    response = client.get(urls["retrieve-not-found"])
    assert response.status_code == 404
    assert response.json()["status"] is False


@pytest.mark.django_db
def test_project_debug_bot_inactive_token(project_client):
    client, urls, _, __ = project_client
    response = client.get(urls["retrieve"])
    data = response.json()["data"]
    assert data["debug_bot"] is True
    assert data["release_bot"] is False


@pytest.mark.django_db
def test_project_debug_bot_active_token(project_client):
    client, urls, instance, _ = project_client
    EnviromentModel.objects.create(user_id=instance.owner_id, project=instance, key="BOT_TOKEN", value="salom")
    EnviromentModel.objects.create(user_id=instance.owner_id, project=instance, key="RELEASE_BOT_TOKEN", value="salom")
    response = client.get(urls["retrieve"])
    data = response.json()["data"]
    assert data["debug_bot"] is True
    assert data["release_bot"] is True
