import pytest
from rest_framework.test import APIClient

from core.apps.cms.models import FieldModel


@pytest.fixture
def api_client():
    client = APIClient()
    # client.force_authenticate(user=None)
    return client


@pytest.fixture
def instance(db):
    return FieldModel._create_fake()


def test_create():
    assert True


def test_update():
    assert True


def test_partial_update():
    assert True


def test_destroy():
    assert True
