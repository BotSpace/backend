"""
Loyiha yaratilganda avtomatik 'users' va 'chat' kolleksiyalari yaratilishi testlari.

Tekshiriladi:
- project create → users + chat kolleksiyalari yaratiladi
- users kolleksiyasida to'g'ri 6 ta field bor
- can_delete False (o'chirib bo'lmaydi)
- idempotent: ikkinchi chaqiruvda dublikat yaratilmaydi
"""

import pytest

from core.apps.api.models.project import ProjectModel
from core.apps.api.services.project import create_default_collections
from core.apps.cms_legacy.models.cms import CollectionModel


@pytest.fixture
def project(db):
    return ProjectModel._create_fake()


@pytest.fixture
def project_with_collections(project):
    create_default_collections(project)
    return project


# ---------------------------------------------------------------------------
# users collection yaratilishi
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_users_collection_created(project_with_collections):
    assert CollectionModel.objects.filter(name="users", project=project_with_collections).exists()


@pytest.mark.django_db
def test_users_collection_has_correct_field_count(project_with_collections):
    collection = CollectionModel.objects.get(name="users", project=project_with_collections)
    assert collection.fields.count() == 6


@pytest.mark.django_db
def test_users_collection_field_names(project_with_collections):
    collection = CollectionModel.objects.get(name="users", project=project_with_collections)
    field_names = set(collection.fields.values_list("name", flat=True))
    expected = {"chat_id", "first_name", "last_name", "username", "last_seen", "created_at"}
    assert field_names == expected


@pytest.mark.django_db
def test_users_collection_chat_id_is_number(project_with_collections):
    collection = CollectionModel.objects.get(name="users", project=project_with_collections)
    field = collection.fields.get(name="chat_id")
    assert field.type == "number"
    assert field.required is True


@pytest.mark.django_db
def test_users_collection_can_delete_false(project_with_collections):
    collection = CollectionModel.objects.get(name="users", project=project_with_collections)
    assert collection.can_delete is False


# ---------------------------------------------------------------------------
# chat collection yaratilishi
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_chat_collection_created(project_with_collections):
    assert CollectionModel.objects.filter(name="chat", project=project_with_collections).exists()


@pytest.mark.django_db
def test_chat_collection_can_delete_false(project_with_collections):
    collection = CollectionModel.objects.get(name="chat", project=project_with_collections)
    assert collection.can_delete is False


# ---------------------------------------------------------------------------
# owner to'g'ri o'rnatilgan
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_users_collection_owner_is_project_owner(project_with_collections):
    collection = CollectionModel.objects.get(name="users", project=project_with_collections)
    assert collection.user_id == project_with_collections.owner_id


# ---------------------------------------------------------------------------
# Idempotentlik: ikkinchi create_default_collections dublikat yaratmasin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_idempotent_no_duplicate_collections(project):
    create_default_collections(project)
    create_default_collections(project)

    users_count = CollectionModel.objects.filter(name="users", project=project).count()
    chat_count = CollectionModel.objects.filter(name="chat", project=project).count()
    assert users_count == 1
    assert chat_count == 1


@pytest.mark.django_db
def test_idempotent_no_duplicate_fields(project):
    create_default_collections(project)
    create_default_collections(project)

    collection = CollectionModel.objects.get(name="users", project=project)
    assert collection.fields.count() == 6
