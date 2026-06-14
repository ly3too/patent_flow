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
