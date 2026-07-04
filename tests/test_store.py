"""Store tests use subprocess mocking — no real Feishu calls."""
import json
from unittest.mock import patch, MagicMock
from patent_flow.store import BitableStore, LarkIM


def _mock_run(output: str):
    def _inner(args, **kwargs):
        m = MagicMock()
        m.stdout = output
        return m
    return _inner


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

    assert any("+record-create" in " ".join(c) for c in calls)


def test_get_case_includes_record_id(monkeypatch):
    def fake_run(args, **kwargs):
        m = MagicMock()
        m.stdout = json.dumps([{"record_id": "rec1", "fields": {"案号": "2026001CNU"}}])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        case = store.get_case("2026001CNU")

    assert case["_record_id"] == "rec1"
    assert case["案号"] == "2026001CNU"


def test_get_case_by_chat_id_filters_on_chat_field(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        m = MagicMock()
        m.stdout = json.dumps([{"record_id": "rec1", "fields": {"案号": "2026001CNU", "群ID": "oc_xxx"}}])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        case = store.get_case_by_chat_id("oc_xxx")

    assert case["案号"] == "2026001CNU"
    assert any("群ID" in " ".join(c) for c in calls)


def test_list_cases_by_node_returns_fields_only(monkeypatch):
    def fake_run(args, **kwargs):
        m = MagicMock()
        m.stdout = json.dumps([
            {"record_id": "rec1", "fields": {"案号": "A"}},
            {"record_id": "rec2", "fields": {"案号": "B"}},
        ])
        return m

    with patch("subprocess.run", side_effect=fake_run):
        store = BitableStore("tok", "tbl_main", "tbl_events")
        cases = store.list_cases_by_node("S6_priority_watch")

    assert [c["案号"] for c in cases] == ["A", "B"]
