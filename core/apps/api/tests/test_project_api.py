import base64
import gzip
import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel

from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.services.project import create_default_collections
from core.apps.api.serializers.project.project import flow_to_gz, gz_to_flow


# --- GLOBAL PATCH FIXTURE ---
@pytest.fixture(autouse=True)
def patch_docker_services():
    with patch("core.apps.api.signals.project.remove_service") as mock_remove, patch(
        "core.apps.api.signals.project.deploy_service"
    ) as mock_deploy, patch("core.apps.api.views.project.deploy_service") as mock_deploy_view, patch(
        "core.apps.api.views.project.set_webhook"
    ):
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
def test_project_debug_recreates_missing_debug_row(project_client):
    client, urls, instance, _ = project_client
    DebugModel.objects.filter(project=instance).delete()
    EnviromentModel.objects.create(
        project=instance,
        key="BOT_TOKEN",
        value="token",
        user=instance.owner,
    )

    response = client.get(urls["debug"])

    assert response.status_code == 200
    assert response.json()["status"] is True
    assert DebugModel.objects.filter(project=instance).exists()


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


@pytest.mark.django_db
def test_release_list_rejects_non_numeric_project(project_client):
    client, _, _, _ = project_client
    response = client.get(reverse("relase-list"), {"project": "global"})

    assert response.status_code == 400
    assert response.json()["status"] is False


# --- FLOW GZIP COMPRESSION TESTS ---

def _make_gz(flow) -> str:
    return base64.b64encode(gzip.compress(json.dumps(flow).encode("utf-8"))).decode("ascii")


@pytest.mark.django_db
def test_flow_gz_helper_roundtrip():
    """flow_to_gz / gz_to_flow roundtrip."""
    flow = {"nodes": [{"id": "1"}], "edges": []}
    gz = flow_to_gz(flow)
    assert isinstance(gz, str)
    assert gz_to_flow(gz) == flow


@pytest.mark.django_db
def test_retrieve_plain_flow_by_default(project_client):
    """?compress param yo'q → plain flow qaytadi, flow_gz yo'q."""
    client, urls, instance, _ = project_client
    instance.flow = {"nodes": [], "edges": []}
    instance.save(update_fields=["flow"])

    response = client.get(urls["retrieve"])
    assert response.status_code == 200
    data = response.json()["data"]
    assert "flow" in data
    assert "flow_gz" not in data


@pytest.mark.django_db
def test_retrieve_compress_returns_flow_gz(project_client):
    """?compress=1 → flow_gz (base64-gzip) qaytadi, flow=None."""
    client, urls, instance, _ = project_client
    original_flow = {"nodes": [{"id": "start"}], "edges": []}
    instance.flow = original_flow
    instance.save(update_fields=["flow"])

    response = client.get(urls["retrieve"], {"compress": "1"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "flow_gz" in data
    assert data["flow"] is None
    decoded = gz_to_flow(data["flow_gz"])
    assert decoded == original_flow


@pytest.mark.django_db
def test_retrieve_compress_true_string(project_client):
    """?compress=true ham ishlashi kerak."""
    client, urls, instance, _ = project_client
    original_flow = {"nodes": [], "edges": []}
    instance.flow = original_flow
    instance.save(update_fields=["flow"])

    response = client.get(urls["retrieve"], {"compress": "true"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "flow_gz" in data
    decoded = gz_to_flow(data["flow_gz"])
    assert decoded == original_flow


@pytest.mark.django_db
def test_partial_update_with_flow_gz(project_client):
    """PATCH flow_gz → flow sifatida saqlanadi."""
    client, urls, instance, _ = project_client
    new_flow = {"nodes": [{"id": "gz-node"}], "edges": []}
    gz = _make_gz(new_flow)

    response = client.patch(urls["retrieve"], data={"flow_gz": gz}, format="json")
    assert response.status_code == 200

    instance.refresh_from_db()
    assert instance.flow == new_flow


@pytest.mark.django_db
def test_partial_update_flow_gz_overrides_plain_flow(project_client):
    """flow_gz va flow ikkalasi kelsa, flow_gz ustun turadi."""
    client, urls, instance, _ = project_client
    gz_flow = {"nodes": [{"id": "from-gz"}], "edges": []}
    plain_flow = {"nodes": [{"id": "from-plain"}], "edges": []}
    gz = _make_gz(gz_flow)

    response = client.patch(urls["retrieve"], data={"flow_gz": gz, "flow": plain_flow}, format="json")
    assert response.status_code == 200

    instance.refresh_from_db()
    assert instance.flow == gz_flow


@pytest.mark.django_db
def test_partial_update_plain_flow_still_works(project_client):
    """Backward-compat: plain flow hali ham ishlaydi (flow_gz yo'q)."""
    client, urls, instance, _ = project_client
    new_flow = {"nodes": [{"id": "plain"}], "edges": []}

    response = client.patch(urls["retrieve"], data={"flow": new_flow}, format="json")
    assert response.status_code == 200

    instance.refresh_from_db()
    assert instance.flow == new_flow


@pytest.mark.django_db
def test_partial_update_bad_flow_gz_returns_400(project_client):
    """Buzuq flow_gz → 400, flow o'zgarmaydi."""
    client, urls, instance, _ = project_client
    original_flow = instance.flow

    response = client.patch(urls["retrieve"], data={"flow_gz": "INVALID_BASE64!!!"}, format="json")
    assert response.status_code == 400

    instance.refresh_from_db()
    assert instance.flow == original_flow


@pytest.mark.django_db
def test_partial_update_valid_b64_but_not_gzip_returns_400(project_client):
    """Valid base64 lekin gzip emas → 400."""
    client, urls, instance, _ = project_client
    bad_gz = base64.b64encode(b"this is not gzip data").decode()

    response = client.patch(urls["retrieve"], data={"flow_gz": bad_gz}, format="json")
    assert response.status_code == 400
