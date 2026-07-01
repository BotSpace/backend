"""Template spec tizimi testlari.

Ishga tushirish:
    cd <worktree> && .venv/bin/python -m pytest core/apps/template/tests/template/test_template_spec.py -v
"""
import copy
import pytest
from unittest.mock import MagicMock, patch

from core.apps.template.services.template_spec import (
    _extract_env_keys_from_flow,
    _find_credential_ids_in_flow,
    _replace_credential_ids_in_flow,
    replace_placeholders_in_flow,
    build_spec_from_project,
)


# ── helper flow'lar ────────────────────────────────────────────────────────────

def _flow_with_creds(*cred_ids):
    return {
        "nodes": [
            {"id": str(i), "type": "AINode", "data": {"credential_id": cid}}
            for i, cid in enumerate(cred_ids)
        ],
        "edges": [],
    }


def _flow_with_env_refs():
    return {
        "nodes": [
            {"id": "1", "type": "SendText", "data": {"text": "Chat: {{env.ADMIN_CHAT_ID}}, key: {{env.SECRET_KEY}}"}},
            {"id": "2", "type": "SendText", "data": {"text": "Repeat: {{env.ADMIN_CHAT_ID}}"}},
        ],
        "edges": [],
    }


# ── env key extraction ─────────────────────────────────────────────────────────

def test_extract_env_keys_basic():
    keys = _extract_env_keys_from_flow(_flow_with_env_refs())
    assert "ADMIN_CHAT_ID" in keys
    assert "SECRET_KEY" in keys


def test_extract_env_keys_dedup():
    keys = _extract_env_keys_from_flow(_flow_with_env_refs())
    assert keys.count("ADMIN_CHAT_ID") == 1


def test_extract_env_keys_empty():
    assert _extract_env_keys_from_flow({}) == []
    assert _extract_env_keys_from_flow(None) == []


# ── credential_id finder ───────────────────────────────────────────────────────

def test_find_credential_ids():
    flow = _flow_with_creds(10, 20)
    ids = _find_credential_ids_in_flow(flow)
    assert ids == {10, 20}


def test_find_credential_ids_string_form():
    flow = {"nodes": [{"data": {"credential_id": "42"}}], "edges": []}
    ids = _find_credential_ids_in_flow(flow)
    assert 42 in ids


def test_find_credential_ids_empty():
    assert _find_credential_ids_in_flow({}) == set()


# ── placeholder almashtirish ───────────────────────────────────────────────────

def test_replace_credential_ids_in_flow():
    flow = _flow_with_creds(10, 20)
    key_map = {10: "openai", 20: "google_sheets"}
    result = _replace_credential_ids_in_flow(flow, key_map)

    for node in result["nodes"]:
        cid = node["data"]["credential_id"]
        assert isinstance(cid, str) and cid.startswith("cred:")

    cids = {n["data"]["credential_id"] for n in result["nodes"]}
    assert "cred:openai" in cids
    assert "cred:google_sheets" in cids


def test_replace_does_not_mutate_original():
    flow = _flow_with_creds(10)
    original = copy.deepcopy(flow)
    _replace_credential_ids_in_flow(flow, {10: "openai"})
    assert flow["nodes"][0]["data"]["credential_id"] == 10  # o'zgarmagan


def test_secret_not_in_placeholder():
    """Placeholder'da faqat logical key bo'lsin, hech qanday secret/token yo'q."""
    flow = _flow_with_creds(99)
    result = _replace_credential_ids_in_flow(flow, {99: "telegram"})
    placeholder = result["nodes"][0]["data"]["credential_id"]
    assert placeholder == "cred:telegram"
    # "bot_token", "api_key" va boshqa secret so'zlar yo'q
    assert "token" not in placeholder or placeholder.startswith("cred:")
    assert "api_key" not in placeholder
    assert "password" not in placeholder


# ── reverse mapping (placeholder → real id) ────────────────────────────────────

def test_replace_placeholders_in_flow():
    flow = {
        "nodes": [{"data": {"credential_id": "cred:openai"}}],
        "edges": [],
    }
    result = replace_placeholders_in_flow(flow, {"openai": 42})
    assert result["nodes"][0]["data"]["credential_id"] == 42


def test_replace_placeholders_unknown_key_stays():
    """Noma'lum placeholder o'zgarishsiz qoladi."""
    flow = {
        "nodes": [{"data": {"credential_id": "cred:unknown_type"}}],
        "edges": [],
    }
    result = replace_placeholders_in_flow(flow, {"openai": 42})
    assert result["nodes"][0]["data"]["credential_id"] == "cred:unknown_type"


def test_replace_placeholders_does_not_mutate():
    flow = {
        "nodes": [{"data": {"credential_id": "cred:openai"}}],
        "edges": [],
    }
    original = copy.deepcopy(flow)
    replace_placeholders_in_flow(flow, {"openai": 1})
    assert flow["nodes"][0]["data"]["credential_id"] == "cred:openai"


# ── build_spec_from_project ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_build_spec_from_project_structure():
    """build_spec_from_project to'g'ri strukturani qaytarishini tekshir."""
    from model_bakery import baker
    from core.apps.api.models import ProjectModel

    project = baker.make(ProjectModel, flow={"nodes": [], "edges": []})

    spec = build_spec_from_project(project)

    assert "flow" in spec
    assert "collections" in spec
    assert "credentials" in spec
    assert "modules" in spec
    assert "envs" in spec
    assert isinstance(spec["collections"], list)
    assert isinstance(spec["credentials"], list)
    assert isinstance(spec["modules"], list)
    assert isinstance(spec["envs"], list)


@pytest.mark.django_db
def test_build_spec_no_secret_in_credentials():
    """spec.credentials'da secret, api_key, password maydon QIYMATI yo'q."""
    from model_bakery import baker
    from core.apps.api.models import ProjectModel

    flow = _flow_with_creds(999)  # mavjud bo'lmagan id — graceful handle

    project = baker.make(ProjectModel, flow=flow)
    spec = build_spec_from_project(project)

    for cred_entry in spec.get("credentials", []):
        for forbidden in ("api_key", "password", "bot_token", "secret"):
            assert forbidden not in cred_entry, f"Credential entry'da '{forbidden}' mavjud: {cred_entry}"


@pytest.mark.django_db
def test_build_spec_env_keys_extracted():
    """Flow'dagi {{env.X}} pattern'lar spec.envs ga tushadi."""
    from model_bakery import baker
    from core.apps.api.models import ProjectModel

    flow = {
        "nodes": [{"id": "1", "data": {"text": "{{env.MY_SECRET_KEY}}"}}],
        "edges": [],
    }
    project = baker.make(ProjectModel, flow=flow)
    spec = build_spec_from_project(project)
    env_keys = [e["key"] for e in spec["envs"]]
    assert "MY_SECRET_KEY" in env_keys


# ── data migration simulyatsiya ────────────────────────────────────────────────

@pytest.mark.django_db
def test_data_migration_required_envs_to_spec():
    """Data migration: required_envs → spec.envs to'g'ri ko'chirilishi."""
    from model_bakery import baker
    from core.apps.template.models import TemplateModel

    tmpl = baker.make(
        TemplateModel,
        slug="test-migration-slug",
        required_envs=[
            {"key": "ADMIN_CHAT_ID", "description": "Admin chat"},
            {"key": "SECRET_TOKEN", "description": "Token"},
        ],
        spec={},
    )

    # Migration logikasini simulyatsiya qilamiz
    spec = {}
    if not spec.get("envs"):
        spec["envs"] = [
            {"key": item["key"], "required": True, "description": item.get("description", "")}
            for item in tmpl.required_envs
            if isinstance(item, dict) and item.get("key")
        ]
    tmpl.spec = spec
    tmpl.save(update_fields=["spec"])
    tmpl.refresh_from_db()

    assert len(tmpl.spec["envs"]) == 2
    keys = [e["key"] for e in tmpl.spec["envs"]]
    assert "ADMIN_CHAT_ID" in keys
    assert "SECRET_TOKEN" in keys


# ── create_from_template serializer validatsiyasi ─────────────────────────────

@pytest.mark.django_db
def test_create_from_template_missing_required_credential():
    """Required credential berilmasa serializer 400 qaytarishi kerak."""
    from model_bakery import baker
    from core.apps.template.models import TemplateModel
    from core.apps.api.serializers.project.project import CreateProjectFromTemplate

    spec = {
        "flow": {"nodes": [], "edges": []},
        "credentials": [{"key": "openai", "type": "openai", "required": True}],
        "modules": [],
        "envs": [],
        "collections": [],
    }
    tmpl = baker.make(TemplateModel, slug="test-cred-required", spec=spec, is_verify=True)

    serializer = CreateProjectFromTemplate(data={
        "template": tmpl.id,
        "name": "Test",
        "token": "123:TOKEN",
        "credentials": {},  # bo'sh — openai berilmagan
    })
    assert not serializer.is_valid()
    assert "credentials" in serializer.errors


@pytest.mark.django_db
def test_create_from_template_missing_required_env():
    """Required env berilmasa serializer 400 qaytarishi kerak."""
    from model_bakery import baker
    from core.apps.template.models import TemplateModel
    from core.apps.api.serializers.project.project import CreateProjectFromTemplate

    spec = {
        "flow": {"nodes": [], "edges": []},
        "credentials": [],
        "modules": [],
        "envs": [{"key": "ADMIN_CHAT_ID", "required": True}],
        "collections": [],
    }
    tmpl = baker.make(TemplateModel, slug="test-env-required", spec=spec, is_verify=True)

    serializer = CreateProjectFromTemplate(data={
        "template": tmpl.id,
        "name": "Test",
        "token": "123:TOKEN",
        "envs": {},  # bo'sh — ADMIN_CHAT_ID berilmagan
    })
    assert not serializer.is_valid()
    assert "envs" in serializer.errors


@pytest.mark.django_db
def test_create_from_template_valid_with_all_required():
    """Barcha required maydonlar to'g'ri berilsa validatsiya o'tadi."""
    from model_bakery import baker
    from core.apps.template.models import TemplateModel
    from core.apps.api.serializers.project.project import CreateProjectFromTemplate

    spec = {
        "flow": {"nodes": [], "edges": []},
        "credentials": [{"key": "openai", "type": "openai", "required": True}],
        "modules": [],
        "envs": [{"key": "ADMIN_CHAT_ID", "required": True}],
        "collections": [],
    }
    tmpl = baker.make(TemplateModel, slug="test-all-valid", spec=spec, is_verify=True)

    serializer = CreateProjectFromTemplate(data={
        "template": tmpl.id,
        "name": "My Bot",
        "token": "123:TOKEN",
        "credentials": {"openai": 42},
        "envs": {"ADMIN_CHAT_ID": "123456789"},
    })
    assert serializer.is_valid(), serializer.errors
