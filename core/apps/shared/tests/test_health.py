"""Smoke tests for the liveness and readiness probes."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


def _post_404_via_drf(client):
    return client.get("/healthz/")


@pytest.mark.django_db
def test_liveness_returns_ok():
    response = APIClient().get("/healthz/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_all_ok_when_dependencies_up():
    with (
        patch("core.apps.shared.views.health._check_database", return_value={"status": "ok"}),
        patch("core.apps.shared.views.health._check_redis", return_value={"status": "ok"}),
        patch("core.apps.shared.views.health._check_mongo", return_value={"status": "ok"}),
    ):
        response = APIClient().get("/readyz/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    assert body["checks"]["mongo"]["status"] == "ok"


@pytest.mark.django_db
def test_readiness_503_when_database_down():
    with (
        patch(
            "core.apps.shared.views.health._check_database",
            return_value={"status": "down", "error": "OperationalError"},
        ),
        patch("core.apps.shared.views.health._check_redis", return_value={"status": "ok"}),
        patch("core.apps.shared.views.health._check_mongo", return_value={"status": "ok"}),
    ):
        response = APIClient().get("/readyz/")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


@pytest.mark.django_db
def test_readiness_503_when_redis_down():
    with (
        patch("core.apps.shared.views.health._check_database", return_value={"status": "ok"}),
        patch(
            "core.apps.shared.views.health._check_redis",
            return_value={"status": "down", "error": "ConnectionError"},
        ),
        patch("core.apps.shared.views.health._check_mongo", return_value={"status": "ok"}),
    ):
        response = APIClient().get("/readyz/")
    assert response.status_code == 503
