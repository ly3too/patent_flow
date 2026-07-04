"""Store tests use subprocess mocking — no real Feishu calls.

The mocked payload shape mirrors the real lark-cli (1.0.53) envelope for
`+record-list --format json`: columnar `data.fields` + `data.data` row
arrays + `data.record_id_list`, not a list of `{record_id, fields}` objects.
This was verified against a live tenant during the first case-init debug run.
"""
import json
from unittest.mock import patch, MagicMock
from patent_flow.store import BitableStore, LarkIM


def _record_list_payload(field_names: list[str], rows: list[list], record_ids: list[str]) -> str:
    return json.dumps({
        "data": {
            "fields": field_names,
            "data": rows,
            "record_id_list": record_ids,
        }
    })


def test_append_event_calls_lark_cli(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        m = MagicMock()
        m.stdout = "{}"
        return m

    monkeypatch.setenv("LEDGER_APP_TOKEN", "tok")
    monkeypatch.setenv("LEDGER_MAIN_TABLE", "tbl_main")
    monkeypatch.setenv("LEDGER_EVENTS_TABLE", "tbl_events")

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        store.append_event("2026001CNU", "agent", "节点跳转", "S1→S2")

    assert any("+record-upsert" in " ".join(c) for c in calls)


def test_get_case_includes_record_id(monkeypatch):
    def fake_run(args, **kwargs):
        m = MagicMock()
        m.stdout = _record_list_payload(["案号"], [["2026001CNU"]], ["rec1"])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        case = store.get_case("2026001CNU")

    assert case["_record_id"] == "rec1"
    assert case["案号"] == "2026001CNU"


def test_get_case_missing_raises_keyerror():
    def fake_run(args, **kwargs):
        m = MagicMock()
        m.stdout = _record_list_payload(["案号"], [], [])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        try:
            store.get_case("nonexistent")
            assert False, "expected KeyError"
        except KeyError:
            pass


def test_get_case_by_chat_id_filters_on_chat_field(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        m = MagicMock()
        m.stdout = _record_list_payload(["案号", "群ID"], [["2026001CNU", "oc_xxx"]], ["rec1"])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        case = store.get_case_by_chat_id("oc_xxx")

    assert case["案号"] == "2026001CNU"
    assert any("群ID" in " ".join(c) for c in calls)


def test_list_cases_by_node_returns_fields_only():
    def fake_run(args, **kwargs):
        m = MagicMock()
        m.stdout = _record_list_payload(["案号"], [["A"], ["B"]], ["rec1", "rec2"])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        cases = store.list_cases_by_node("S6_priority_watch")

    assert [c["案号"] for c in cases] == ["A", "B"]


def test_lark_im_send_uses_chat_id_flag():
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        m = MagicMock()
        m.stdout = "{}"
        return m

    with patch("subprocess.run", side_effect=fake_run):
        LarkIM().send("oc_xxx", "hello")

    joined = " ".join(calls[0])
    assert "--chat-id" in joined and "oc_xxx" in joined
    assert "--receive-id" not in joined
