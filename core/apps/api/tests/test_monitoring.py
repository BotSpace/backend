"""Monitoring endpoint uchun testlar."""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.api.services.monitoring import prom_query, get_project_monitoring
from core.apps.api.services.project import create_default_collections


# ---------------------------------------------------------------------------
# prom_query unit testi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mock_json, expected",
    [
        (
            {"data": {"result": [{"value": [1700000000, "0.00042"]}]}},
            0.00042,
        ),
        ({"data": {"result": []}}, None),
        ({"data": {}}, None),
    ],
)
def test_prom_query_parses_result(mock_json, expected):
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_json
    mock_resp.raise_for_status.return_value = None

    with patch("core.apps.api.services.monitoring.requests.get", return_value=mock_resp):
        result = prom_query('up{job="test"}')

    assert result == expected


def test_prom_query_returns_none_on_exception():
    with patch("core.apps.api.services.monitoring.requests.get", side_effect=Exception("timeout")):
        result = prom_query("up")
    assert result is None


# ---------------------------------------------------------------------------
# get_project_monitoring unit testi
# ---------------------------------------------------------------------------


def test_get_project_monitoring_prom_unavailable():
    with patch("core.apps.api.services.monitoring.prom_query", return_value=None), \
         patch("core.apps.api.services.monitoring._files_bytes", return_value=5000), \
         patch("core.apps.api.services.monitoring._cms_bytes", return_value=200):
        data = get_project_monitoring(project_id=1)

    assert data["prometheus_available"] is False
    assert data["cpu_cores"] is None
    assert data["memory_bytes"] is None
    assert data["net_rx_bps"] is None
    assert data["net_tx_bps"] is None
    assert data["disk_bytes"] == 5200
    assert data["disk_files_bytes"] == 5000
    assert data["disk_cms_bytes"] == 200


def test_get_project_monitoring_prom_available():
    def _prom(query):
        if "cpu" in query:
            return 0.001
        if "memory" in query:
            return 8000000.0
        if "receive" in query:
            return 100.0
        if "transmit" in query:
            return 50.0
        return None

    with patch("core.apps.api.services.monitoring.prom_query", side_effect=_prom), \
         patch("core.apps.api.services.monitoring._files_bytes", return_value=0), \
         patch("core.apps.api.services.monitoring._cms_bytes", return_value=0):
        data = get_project_monitoring(project_id=42)

    assert data["prometheus_available"] is True
    assert data["cpu_cores"] == 0.001
    assert data["memory_bytes"] == 8000000.0
    assert data["net_rx_bps"] == 100.0
    assert data["net_tx_bps"] == 50.0


# ---------------------------------------------------------------------------
# API endpoint integratsiya testi
# ---------------------------------------------------------------------------


@pytest.fixture
def monitoring_client(db):
    instance = ProjectModel._create_fake()
    create_default_collections(instance)
    client = APIClient()
    client.force_authenticate(instance.owner)
    url = reverse("project-monitoring", kwargs={"pk": instance.pk})
    return client, url, instance


@pytest.mark.django_db
def test_monitoring_endpoint_returns_200(monitoring_client):
    client, url, project = monitoring_client

    with patch("core.apps.api.services.monitoring.prom_query", return_value=None), \
         patch("core.apps.api.services.monitoring._files_bytes", return_value=1024), \
         patch("core.apps.api.services.monitoring._cms_bytes", return_value=0):
        resp = client.get(url)

    assert resp.status_code == 200
    data = resp.json()
    assert "prometheus_available" in data
    assert "disk_bytes" in data
    assert "disk_files_bytes" in data
    assert "disk_cms_bytes" in data
    assert data["disk_files_bytes"] == 1024


@pytest.mark.django_db
def test_monitoring_endpoint_403_for_other_user(monitoring_client):
    _, url, _ = monitoring_client

    other = ProjectModel._create_fake()
    other_client = APIClient()
    other_client.force_authenticate(other.owner)

    with patch("core.apps.api.services.monitoring.prom_query", return_value=None):
        resp = other_client.get(url)

    assert resp.status_code == 404


@pytest.mark.django_db
def test_monitoring_endpoint_requires_auth(monitoring_client):
    _, url, _ = monitoring_client
    anon = APIClient()
    resp = anon.get(url)
    assert resp.status_code == 401
