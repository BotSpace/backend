"""cms shared-tenancy scoping unit-testlari (Mongo'siz — pure helperlar).

Tenancy endi yagona holat — har so'rov `_project_id` bilan filtrlanadi.
"""

from core.apps.cms.services import mongo


def test_scoped_injects_tenant():
    f = mongo._scoped(7, {"status": "new"})
    assert f[mongo.TENANT_FIELD] == 7           # tenant majburiy qo'shildi
    assert f["status"] == "new"                 # foydalanuvchi filtri saqlandi
    assert f["_deleted_at"] is None             # soft-delete filtri


def test_stamp_create_tags_tenant():
    d = mongo._stamp_create({"a": 1}, 9)
    assert d[mongo.TENANT_FIELD] == 9
    assert d["_version"] == 1


def test_serialize_strips_tenant():
    out = mongo._serialize({mongo.TENANT_FIELD: 3, "x": 1})
    assert mongo.TENANT_FIELD not in out        # ichki maydon API'da ko'rinmaydi
    assert out["x"] == 1
