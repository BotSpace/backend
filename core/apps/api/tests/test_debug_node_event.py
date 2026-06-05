from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel


@pytest.fixture
def plan(db):
    return PlanModel._create_fake()


@pytest.fixture
def project(db, plan):
    return ProjectModel._create_fake()


@pytest.fixture
def client():
    return APIClient()


NODE_EVENT_URL = "/api/debug/node-event/"
INTERNAL_TOKEN = "test-internal-secret"


@pytest.mark.django_db
def test_node_event_publishes_ws(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish") as mock_publish:
        resp = client.post(
            NODE_EVENT_URL,
            data={
                "project_id": project.pk,
                "chat_id": 42,
                "node_id": "n1",
                "node_type": "SendTextMessageNode",
                "status": "running",
                "error": "",
                "ts": 1700000000000,
                "run_id": 7,
                "seq": 12,
            },
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200
    assert resp.data["ok"] is True
    mock_publish.assert_called_once()
    assert mock_publish.call_args[0][0] == project.owner_id
    schema = mock_publish.call_args[0][1]
    assert schema.run_id == 7
    assert schema.seq == 12


@pytest.mark.django_db
def test_node_event_wrong_token_returns_403(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        NODE_EVENT_URL,
        data={"project_id": project.pk, "chat_id": 1, "node_id": "n1", "status": "running"},
        format="json",
        HTTP_X_INTERNAL_TOKEN="wrong",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_node_event_unknown_project_returns_404(client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        NODE_EVENT_URL,
        data={"project_id": 999999, "chat_id": 1, "node_id": "n1", "status": "running"},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_node_event_uuid_lookup(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish") as mock_publish:
        resp = client.post(
            NODE_EVENT_URL,
            data={"project_id": str(project.uuid), "chat_id": 7, "node_id": "n2", "status": "success"},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200
    mock_publish.assert_called_once()
