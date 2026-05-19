"""Tests for SoftDeleteModel against a real ORM model (TransactionModel)."""

import pytest

from core.apps.payment.models.transaction import TransactionModel


@pytest.mark.django_db
def test_default_manager_hides_soft_deleted(user):
    alive = TransactionModel.objects.create(user=user, amount=100)
    dead = TransactionModel.objects.create(user=user, amount=200)
    dead.delete()
    assert TransactionModel.objects.filter(pk=alive.pk).exists()
    assert not TransactionModel.objects.filter(pk=dead.pk).exists()


@pytest.mark.django_db
def test_all_objects_returns_deleted(user):
    t = TransactionModel.objects.create(user=user, amount=100)
    t.delete()
    assert TransactionModel.all_objects.filter(pk=t.pk).exists()
    assert TransactionModel.all_objects.dead().count() == 1


@pytest.mark.django_db
def test_restore_brings_back(user):
    t = TransactionModel.objects.create(user=user, amount=100)
    t.delete()
    t.restore()
    assert TransactionModel.objects.filter(pk=t.pk).exists()


@pytest.mark.django_db
def test_hard_delete_removes_row(user):
    t = TransactionModel.objects.create(user=user, amount=100)
    pk = t.pk
    t.delete(hard=True)
    assert not TransactionModel.all_objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_queryset_delete_is_soft(user):
    TransactionModel.objects.create(user=user, amount=100)
    TransactionModel.objects.create(user=user, amount=200)
    TransactionModel.objects.all().delete()
    assert TransactionModel.objects.count() == 0
    assert TransactionModel.all_objects.dead().count() == 2
