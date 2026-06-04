"""IDOR himoyasi: boshqa foydalanuvchining loyihasidagi cms ma'lumotlariga
project_id orqali kirib bo'lmasligi kerak (X-User-Id / JWT bilan ham)."""

import pytest
from model_bakery import baker
from rest_framework.exceptions import NotFound

from core.apps.cms.models import Collection
from core.apps.cms.views._common import get_collection_or_404, get_project_or_404

pytestmark = pytest.mark.django_db


def _user():
    return baker.make("accounts.User")


def test_get_project_blocks_foreign_owner():
    owner = _user()
    attacker = _user()
    project = baker.make("api.ProjectModel", owner=owner)

    # Egasi — o'tadi
    assert get_project_or_404(project.pk, user=owner).pk == project.pk
    # Begona foydalanuvchi — NotFound (mavjudligini ham oshkor qilmaydi)
    with pytest.raises(NotFound):
        get_project_or_404(project.pk, user=attacker)


def test_staff_bypass():
    owner = _user()
    staff = baker.make("accounts.User", is_staff=True)
    project = baker.make("api.ProjectModel", owner=owner)
    assert get_project_or_404(project.pk, user=staff).pk == project.pk


def test_get_collection_blocks_foreign_owner():
    owner = _user()
    attacker = _user()
    project = baker.make("api.ProjectModel", owner=owner)
    coll = Collection.objects.create(project=project, owner=owner, name="users", system=True)

    assert get_collection_or_404(project_id=project.pk, name="users", user=owner).pk == coll.pk
    with pytest.raises(NotFound):
        get_collection_or_404(project_id=project.pk, name="users", user=attacker)


def test_no_user_is_trusted_path():
    # user=None — ishonchli system yo'li (egalik tekshirilmaydi).
    owner = _user()
    project = baker.make("api.ProjectModel", owner=owner)
    assert get_project_or_404(project.pk).pk == project.pk
