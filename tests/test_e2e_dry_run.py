"""Dry-run e2e: validates the full transition flow with all I/O mocked."""
from unittest.mock import patch, MagicMock
import pytest


def _noop(*args, **kwargs):
    m = MagicMock()
    m.stdout = "{}"
    return m


@pytest.mark.skip(reason="requires env vars and lark-cli; run manually")
def test_transition_dry_run(monkeypatch):
    monkeypatch.setenv("LEDGER_APP_TOKEN", "fake_token")
    monkeypatch.setenv("LEDGER_MAIN_TABLE", "tbl_main")
    monkeypatch.setenv("LEDGER_EVENTS_TABLE", "tbl_events")

    with patch("subprocess.run", side_effect=_noop):
        from patent_flow.transition import transition
        transition(
            case_no="2026001CNU",
            from_node="S1_mining",
            to_node="S2_search",
            evidence="IPR 确认三要素完整",
            record_id="rec_001",
            chat_id="oc_xxx",
            doc_token="doc_xxx",
            state_block_id="blk_xxx",
            case_title="电视挂架自适应卡扣",
        )
