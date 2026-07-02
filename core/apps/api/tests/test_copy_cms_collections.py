"""Unit tests for the cmsv2 template-copy classification logic.

These are pure-function tests (no Mongo / no DB) covering catalog-vs-runtime
classification and field inference from a sample document.
"""

from core.apps.api.services.project import (
    _new_fields_from_sample,
    _node_collection_name,
    collection_is_catalog,
)


def _load_list(name):
    return {"id": "n1", "type": "LoadCollectionListNode", "data": {"collection_name": name}}


def _load_item_nested(name):
    return {"id": "n2", "type": "LoadCollectionItemNode", "data": {"collection": {"name": name}}}


def _save(name):
    return {"id": "n3", "type": "CollectionNode", "data": {"collection_name": name}}


def test_catalog_when_read_only():
    flow = {"nodes": [_load_list("doctors")]}
    assert collection_is_catalog(flow, "doctors") is True


def test_catalog_with_nested_collection_name():
    flow = {"nodes": [_load_item_nested("doctors")]}
    assert collection_is_catalog(flow, "doctors") is True


def test_not_catalog_when_written():
    flow = {"nodes": [_load_list("consultations"), _save("consultations")]}
    assert collection_is_catalog(flow, "consultations") is False


def test_not_catalog_when_only_written():
    flow = {"nodes": [_save("orders")]}
    assert collection_is_catalog(flow, "orders") is False


def test_not_catalog_when_never_referenced():
    flow = {"nodes": [_load_list("doctors")]}
    assert collection_is_catalog(flow, "leads") is False


def test_users_and_chat_are_never_catalog():
    flow = {"nodes": [_load_list("users"), _load_list("chat")]}
    assert collection_is_catalog(flow, "users") is False
    assert collection_is_catalog(flow, "chat") is False


def test_flow_as_bare_list_is_supported():
    flow = [_load_list("doctors")]
    assert collection_is_catalog(flow, "doctors") is True


def test_flow_none_or_garbage_is_safe():
    assert collection_is_catalog(None, "doctors") is False
    assert collection_is_catalog({"nodes": "nope"}, "doctors") is False
    assert collection_is_catalog(42, "doctors") is False


def test_node_collection_name_variants():
    assert _node_collection_name({"collection_name": "a"}) == "a"
    assert _node_collection_name({"collection": {"name": "b"}}) == "b"
    assert _node_collection_name({"collection": "c"}) == "c"
    assert _node_collection_name({}) is None
    assert _node_collection_name({"collection": {}}) is None


def test_field_inference_from_sample_skips_underscore_keys():
    sample = {
        "_id": "x",
        "_created_at": "t",
        "name": "Dr. House",
        "specialty": "Diagnostics",
    }

    class _FakeColl:
        pass

    fields = _new_fields_from_sample(sample, _FakeColl())
    names = [f.name for f in fields]
    assert names == ["name", "specialty"]
    assert all(f.kind == "text" for f in fields)


def test_field_inference_handles_non_dict():
    class _FakeColl:
        pass

    assert _new_fields_from_sample(None, _FakeColl()) == []
    assert _new_fields_from_sample("nope", _FakeColl()) == []


def test_catalog_via_collection_data_button():
    # Inline keyboard tugmalari kolleksiyadan render bo'lsa — bu ham O'QISH.
    flow = {"nodes": [{
        "id": "n5", "type": "EditOrSendMessageNode",
        "data": {"rows": [{"columns": [{"collectionData": {"collection": "services", "field": "title"}}]}]},
    }]}
    assert collection_is_catalog(flow, "services") is True


def test_not_catalog_when_collection_data_read_but_updated():
    flow = {"nodes": [
        {"id": "n5", "type": "EditOrSendMessageNode",
         "data": {"rows": [{"columns": [{"collectionData": {"collection": "items"}}]}]}},
        {"id": "n6", "type": "UpdateCollectionNode", "data": {"collection_name": "items"}},
    ]}
    assert collection_is_catalog(flow, "items") is False
