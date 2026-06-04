"""cmsv2 system collections (users/chat) auto-creation tests."""

import pytest
from model_bakery import baker

from core.apps.cms.models.collection import Collection
from core.apps.cms.services.system_collections import ensure_system_collections

pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    return baker.make("api.ProjectModel")


def test_creates_users_and_chat(project):
    ensure_system_collections(project)
    names = set(
        Collection.objects.filter(project=project, deleted_at__isnull=True).values_list(
            "name", flat=True
        )
    )
    assert {"users", "chat"} <= names


def test_users_schema_matches_engine_writes(project):
    ensure_system_collections(project)
    users = Collection.objects.get(project=project, name="users")
    assert users.system is True
    assert users.can_delete is False
    fields = {f.name: f for f in users.fields.all()}
    assert set(fields) == {"chat_id", "first_name", "last_name", "username", "last_seen", "created_at"}
    assert fields["chat_id"].kind == "int"
    assert fields["chat_id"].required is True


def test_idempotent(project):
    ensure_system_collections(project)
    ensure_system_collections(project)
    assert Collection.objects.filter(project=project, name="users", deleted_at__isnull=True).count() == 1
    users = Collection.objects.get(project=project, name="users")
    assert users.fields.count() == 6


def test_existing_non_system_collection_upgraded(project):
    Collection.objects.create(project=project, owner=project.user, name="users", system=False)
    ensure_system_collections(project)
    users = Collection.objects.get(project=project, name="users")
    assert users.system is True
