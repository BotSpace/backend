"""Root pytest fixtures shared across all apps."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient


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
