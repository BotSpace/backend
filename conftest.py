"""Root pytest fixtures shared across all apps."""

from __future__ import annotations

import sys
import types


def _stub_kubernetes() -> None:
    """Install minimal stubs for the `kubernetes` package when it is absent.

    The Docker image has `kubernetes` installed; the local venv may not.
    Stubs must be injected before Django app-loading so that imports inside
    core.apps.api.services.kubernetes_service do not raise ImportError.
    """
    _mods = (
        "kubernetes",
        "kubernetes.client",
        "kubernetes.client.rest",
        "kubernetes.config",
        "kubernetes.watch",
    )
    for _mod in _mods:
        if _mod not in sys.modules:
            sys.modules[_mod] = types.ModuleType(_mod)

    _rest = sys.modules["kubernetes.client.rest"]
    if not hasattr(_rest, "ApiException"):
        _rest.ApiException = type("ApiException", (Exception,), {})  # type: ignore[attr-defined]

    _client = sys.modules["kubernetes.client"]
    for _attr in (
        "V1Pod", "V1PodList", "CoreV1Api", "AppsV1Api", "V1Deployment",
        "V1DeploymentList", "V1Container", "V1PodSpec", "V1ObjectMeta",
        "V1EnvVar", "Configuration", "ApiClient",
    ):
        if not hasattr(_client, _attr):
            setattr(_client, _attr, type(_attr, (), {}))

    # Wire up parent-child references so `from kubernetes.client.rest import X` works
    sys.modules["kubernetes"].client = _client  # type: ignore[attr-defined]
    _client.rest = _rest  # type: ignore[attr-defined]


# Run stub injection at module import time — this file is the first conftest
# collected and runs before pytest-django triggers Django settings loading.
try:
    import kubernetes  # noqa: F401 — real package present, nothing to stub
except ImportError:
    _stub_kubernetes()


def pytest_configure(config):  # noqa: ANN001
    """Re-apply stubs after pytest config phase in case Django cleared sys.modules."""
    try:
        import kubernetes  # noqa: F401
    except ImportError:
        _stub_kubernetes()


import pytest  # noqa: E402 — after stubs
from django.contrib.auth import get_user_model  # noqa: E402
from model_bakery import baker  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402


@pytest.fixture
def user(db):
    """A persisted regular user."""
    return get_user_model()._create_fake()


@pytest.fixture
def other_user(db):
    """A second user (for permission tests)."""
    return baker.make(get_user_model(), phone="+99899999999")


@pytest.fixture
def api_client():
    """Anonymous APIClient."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient authenticated as the default fixture user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client
