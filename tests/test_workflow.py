from datetime import date

import pytest

from patent_flow import workflow
from patent_flow.nodes.base import NodeResult


class FakeStore:
    def __init__(self, cases_by_node: dict[str, list[dict]]):
        self._cases = cases_by_node

    def list_cases_by_node(self, node):
        return self._cases.get(node, [])

    def get_case_by_chat_id(self, chat_id):
        for cases in self._cases.values():
            for case in cases:
                if case.get("群ID") == chat_id:
                    return case
        raise KeyError(chat_id)


# --- dispatch ----------------------------------------------------------------

def test_dispatch_routes_to_the_current_nodes_handler():
    case = {"当前节点": "S1_mining"}
    result = workflow.dispatch(
        case,
        three_elements={"技术问题": "a", "技术方案": "b", "技术效果": "c"},
        ipr_confirmed=True,
    )
    assert result.to_node == "S2_search"


def test_dispatch_rejects_illegal_transition(monkeypatch):
    case = {"当前节点": "S1_mining"}
    bogus = NodeResult(to_node="S8_annuity", evidence="", summary="")
    monkeypatch.setattr(workflow, "get_handler", lambda node: (lambda case, **kw: bogus))
    with pytest.raises(ValueError, match="Illegal transition"):
        workflow.dispatch(case)


def test_dispatch_allows_staying_put():
    # A "no transition yet" result (e.g. S6 with no reminder tier hit today)
    # must not trip the state-machine guard.
    result = workflow.dispatch({"当前节点": "S6_priority_watch", "申请日": "2026-01-01"}, today=date(2026, 1, 2))
    assert result.to_node is None


# --- apply_result --------------------------------------------------------------

def test_apply_result_skips_transition_when_to_node_is_none(monkeypatch):
    calls = []
    monkeypatch.setattr(workflow, "_transition", lambda **kw: calls.append(kw))

    result = NodeResult(to_node=None, evidence="", summary="仍在等待")
    workflow.apply_result(
        "2026001CNU", "S1_mining", result,
        record_id="rec1", chat_id="oc1", doc_token="doc1",
        state_block_id="agent_state", case_title="标题",
    )
    assert calls == []


def test_apply_result_calls_transition_when_to_node_is_set(monkeypatch):
    calls = []
    monkeypatch.setattr(workflow, "_transition", lambda **kw: calls.append(kw))

    result = NodeResult(to_node="S2_search", evidence="确认完毕", summary="")
    workflow.apply_result(
        "2026001CNU", "S1_mining", result,
        record_id="rec1", chat_id="oc1", doc_token="doc1",
        state_block_id="agent_state", case_title="标题",
    )
    assert len(calls) == 1
    assert calls[0]["to_node"] == "S2_search"
    assert calls[0]["case_no"] == "2026001CNU"


# --- scan_deadlines --------------------------------------------------------------

def test_scan_deadlines_only_returns_cases_that_need_a_human():
    store = FakeStore({
        "S6_priority_watch": [{"案号": "A", "当前节点": "S6_priority_watch", "申请日": "2026-01-01"}],
        "S8_annuity": [{"案号": "B", "当前节点": "S8_annuity", "年费到期日": "2099-01-01"}],
    })
    # A is exactly 30 days from its priority deadline (2026-11-01); B is far off
    today = date(2026, 10, 2)
    due = workflow.scan_deadlines(today=today, store=store)
    assert [d["案号"] for d in due] == ["A"]
