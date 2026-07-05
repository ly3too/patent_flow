"""python -m patent_flow <cmd> entry point."""
import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import date

from . import workflow
from .case_no import generate_case_no
from .nodes.base import NodeResult
from .registry import NODE_REGISTRY
from .store import BitableStore

DEFAULT_STATE_BLOCK_ID = "agent_state"


def main() -> None:
    parser = argparse.ArgumentParser(prog="patent-flow")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show how many active cases sit on each node")

    sub.add_parser("new-case-no", help="Generate a unique case number (YYYYMMDD + 5 random letters)")

    p_transition = sub.add_parser("transition", help="Advance a case to the next node")
    p_transition.add_argument("case_no")
    p_transition.add_argument("to_node")
    p_transition.add_argument("--evidence", default="")
    _add_doc_sync_args(p_transition)

    p_run_node = sub.add_parser(
        "run-node",
        help="Dispatch the case's current node handler with structured inputs and apply the result",
    )
    p_run_node.add_argument("case_no")
    p_run_node.add_argument("--inputs", default="{}", help="JSON object of node handler kwargs")
    _add_doc_sync_args(p_run_node)

    sub.add_parser("scan-deadlines", help="Scan bitable for cases near a cron-driven deadline (S6/S8)")

    args = parser.parse_args()

    if args.cmd == "status":
        _cmd_status()
    elif args.cmd == "new-case-no":
        _cmd_new_case_no()
    elif args.cmd == "transition":
        _cmd_transition(args)
    elif args.cmd == "run-node":
        _cmd_run_node(args)
    elif args.cmd == "scan-deadlines":
        _cmd_scan_deadlines()


def _add_doc_sync_args(p: argparse.ArgumentParser) -> None:
    """Fields transition() needs to sync the doc/chat. All optional — default
    to what's already on the bitable record so callers only override when
    the record doesn't have them yet (e.g. state_block_id, case_title)."""
    p.add_argument("--chat-id", default=None, help="default: case's 群ID field")
    p.add_argument("--doc-token", default=None, help="default: case's 案件主文档 field")
    p.add_argument("--state-block-id", default=None, help=f"default: {DEFAULT_STATE_BLOCK_ID!r}")
    p.add_argument("--case-title", default=None, help="default: case's 案件名 field, or case_no")


def _resolve_doc_sync_args(case: dict, args) -> dict:
    return {
        "chat_id": args.chat_id or case["群ID"],
        "doc_token": args.doc_token or case["案件主文档"],
        "state_block_id": args.state_block_id or DEFAULT_STATE_BLOCK_ID,
        "case_title": args.case_title or case.get("案件名", case["案号"]),
    }


def _store() -> BitableStore:
    return BitableStore(
        app_token=os.environ["LEDGER_APP_TOKEN"],
        main_table_id=os.environ["LEDGER_MAIN_TABLE"],
        events_table_id=os.environ["LEDGER_EVENTS_TABLE"],
    )


def _cmd_new_case_no() -> None:
    print(generate_case_no(_store()))


def _cmd_status() -> None:
    store = _store()
    for node in NODE_REGISTRY:
        count = len(store.list_cases_by_node(node))
        print(f"{node}: {count}")


def _cmd_transition(args) -> None:
    store = _store()
    try:
        case = store.get_case(args.case_no)
        from_node = case["当前节点"]
        workflow.apply_result(
            case_no=args.case_no,
            from_node=from_node,
            result=NodeResult(to_node=args.to_node, evidence=args.evidence, summary=args.evidence),
            record_id=case["_record_id"],
            **_resolve_doc_sync_args(case, args),
        )
        print(f"Transitioned {args.case_no}: {from_node} → {args.to_node}")
    except (ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_run_node(args) -> None:
    store = _store()
    try:
        case = store.get_case(args.case_no)
        from_node = case["当前节点"]
        inputs = json.loads(args.inputs)
        result = workflow.dispatch(case, **inputs)
        workflow.apply_result(
            case_no=args.case_no,
            from_node=from_node,
            result=result,
            record_id=case["_record_id"],
            **_resolve_doc_sync_args(case, args),
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    except (ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_scan_deadlines() -> None:
    due = workflow.scan_deadlines(today=date.today())
    for item in due:
        result = item["result"]
        print(f"[{item['当前节点']}] {item['案号']}: {result.summary}")
    if not due:
        print("No cases due for a reminder today.")


if __name__ == "__main__":
    main()
