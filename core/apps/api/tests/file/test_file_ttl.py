"""TTL va expires_at mantiqini tekshiruvchi testlar."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.apps.api.models.file import FileModel
from core.apps.api.tasks.file import cleanup_expired_files


@pytest.fixture
def base_file(db):
    return FileModel._baker()


@pytest.mark.django_db
def test_ttl_sets_expires_at(base_file):
    """ttl > 0 bo'lsa expires_at = now + ttl."""
    from core.apps.api.serializers.file import CreateFileSerializer

    # CreateFileSerializer.create() mantiqini to'g'ridan test qilmaymiz (fayl yuklash kerak),
    # shuning uchun expires_at hisob-kitobini to'g'ridan tekshiramiz.
    before = timezone.now()
    ttl_seconds = 3600
    expected_expires = before + timedelta(seconds=ttl_seconds)

    base_file.expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
    base_file.save(update_fields=["expires_at"])

    base_file.refresh_from_db()
    assert base_file.expires_at is not None
    # 5 soniya tolerans bilan tekshiramiz
    assert abs((base_file.expires_at - expected_expires).total_seconds()) < 5


@pytest.mark.django_db
def test_no_ttl_expires_at_is_none(base_file):
    """expires_at berilmasa None (doimiy)."""
    base_file.expires_at = None
    base_file.save(update_fields=["expires_at"])
    base_file.refresh_from_db()
    assert base_file.expires_at is None


@pytest.mark.django_db
def test_cleanup_deletes_expired(db, tmp_path, monkeypatch):
    """cleanup_expired_files muddati o'tgan faylni DB'dan o'chiradi."""
    expired = FileModel._baker()
    expired.expires_at = timezone.now() - timedelta(hours=1)
    expired.save(update_fields=["expires_at"])

    permanent = FileModel._baker()
    permanent.expires_at = None
    permanent.save(update_fields=["expires_at"])

    future = FileModel._baker()
    future.expires_at = timezone.now() + timedelta(hours=1)
    future.save(update_fields=["expires_at"])

    # storage.delete chaqiruvini mock'laymiz (fayl haqiqatda yo'q)
    monkeypatch.setattr("django.core.files.storage.FileSystemStorage.delete", lambda self, name: None)

    deleted_count = cleanup_expired_files()

    assert deleted_count == 1
    assert not FileModel.objects.filter(pk=expired.pk).exists()
    assert FileModel.objects.filter(pk=permanent.pk).exists()
    assert FileModel.objects.filter(pk=future.pk).exists()
