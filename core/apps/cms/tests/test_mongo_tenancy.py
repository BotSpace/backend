"""cms shared-tenancy scoping unit-testlari (Mongo'siz — pure helperlar)."""

from core.apps.cms.services import mongo


def test_scoped_off_no_tenant(monkeypatch):
    monkeypatch.setattr(mongo, "SHARED_TENANCY", False)
    f = mongo._scoped(7, {"status": "new"})
    assert mongo.TENANT_FIELD not in f          # eski rejim: tenant maydoni yo'q
    assert f["_deleted_at"] is None             # soft-delete filtri bor
    assert f["status"] == "new"


def test_scoped_on_injects_tenant(monkeypatch):
    monkeypatch.setattr(mongo, "SHARED_TENANCY", True)
    f = mongo._scoped(7, {"status": "new"})
    assert f[mongo.TENANT_FIELD] == 7           # tenant majburiy qo'shildi
    assert f["status"] == "new"                 # foydalanuvchi filtri saqlandi
    assert f["_deleted_at"] is None


def test_stamp_create_tags_tenant(monkeypatch):
    monkeypatch.setattr(mongo, "SHARED_TENANCY", True)
    d = mongo._stamp_create({"a": 1}, 9)
    assert d[mongo.TENANT_FIELD] == 9
    assert d["_version"] == 1


def test_stamp_create_off_no_tenant(monkeypatch):
    monkeypatch.setattr(mongo, "SHARED_TENANCY", False)
    d = mongo._stamp_create({"a": 1}, 9)
    assert mongo.TENANT_FIELD not in d


def test_serialize_strips_tenant():
    out = mongo._serialize({mongo.TENANT_FIELD: 3, "x": 1})
    assert mongo.TENANT_FIELD not in out        # ichki maydon API'da ko'rinmaydi
    assert out["x"] == 1
