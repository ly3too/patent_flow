"""Top-level orchestration for skills/workflow/patent-flow — design.md §7's
decision loop: identify_case → load_case → dispatch → transition guard →
sync. This module owns no LLM reasoning; it composes `store.py` (reads),
the node `registry` (business decision), and `transition.py` (the only
legal state-write path).
"""
from __future__ import annotations

import os
from datetime import date

from .nodes.base import NodeResult
from .registry import get_handler
from .state_machine import validate_transition
from .store import BitableStore
from .transition import transition as _transition

CRON_SCANNED_NODES = ("S6_priority_watch", "S8_annuity")


def _ledger_store() -> BitableStore:
    return BitableStore(
        app_token=os.environ["LEDGER_APP_TOKEN"],
        main_table_id=os.environ["LEDGER_MAIN_TABLE"],
        events_table_id=os.environ["LEDGER_EVENTS_TABLE"],
    )


def identify_case(chat_id: str, store: BitableStore | None = None) -> str:
    """一案一群：群 ID ↔ 案号一一映射，反查案号。"""
    store = store or _ledger_store()
    case = store.get_case_by_chat_id(chat_id)
    return case["案号"]


def dispatch(case: dict, **inputs) -> NodeResult:
    """Route to the task-layer handler for the case's current node and get
    its decision. Raises ValueError immediately if the handler proposes an
    illegal jump — fail fast, before any message/card is composed."""
    current_node = case["当前节点"]
    handler = get_handler(current_node)
    result = handler(case, **inputs)
    if result.to_node is not None:
        validate_transition(current_node, result.to_node)
    return result


def apply_result(
    case_no: str,
    from_node: str,
    result: NodeResult,
    *,
    record_id: str,
    chat_id: str,
    doc_token: str,
    state_block_id: str,
    case_title: str,
) -> None:
    """Apply a NodeResult: transition() only if a legal to_node was decided;
    otherwise the case stays put (still waiting on a human_gate)."""
    if result.to_node is None:
        return
    _transition(
        case_no=case_no,
        from_node=from_node,
        to_node=result.to_node,
        evidence=result.evidence,
        record_id=record_id,
        chat_id=chat_id,
        doc_token=doc_token,
        state_block_id=state_block_id,
        case_title=case_title,
    )


def scan_deadlines(today: date | None = None, store: BitableStore | None = None) -> list[dict]:
    """Cron entry point for S6/S8 (design.md §7.2's cron/webhook wakeups).

    Dispatches every case sitting on a cron-driven node with no pm_decision,
    so each handler only returns a reminder (needs_human) or stays silent.
    Returns one summary dict per case that needs attention — the caller
    (workflow skill / hooks/*.yaml) is responsible for actually sending the
    reminder card and appending the event.
    """
    today = today or date.today()
    store = store or _ledger_store()

    due = []
    for node in CRON_SCANNED_NODES:
        for case in store.list_cases_by_node(node):
            result = dispatch(case, today=today)
            if result.needs_human:
                due.append({"案号": case["案号"], "当前节点": node, "result": result})
    return due
