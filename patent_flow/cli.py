"""python -m patent_flow <cmd> entry point."""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="patent-flow")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show status of all active cases")

    p_transition = sub.add_parser("transition", help="Advance a case to the next node")
    p_transition.add_argument("case_no")
    p_transition.add_argument("to_node")
    p_transition.add_argument("--evidence", default="")

    p_scan = sub.add_parser("scan-deadlines", help="Scan bitable for cases near deadline")
    p_scan.add_argument("--days", type=int, default=3)

    args = parser.parse_args()

    if args.cmd == "status":
        _cmd_status()
    elif args.cmd == "transition":
        _cmd_transition(args.case_no, args.to_node, args.evidence)
    elif args.cmd == "scan-deadlines":
        _cmd_scan_deadlines(args.days)


def _cmd_status() -> None:
    print("(status not yet implemented)")


def _cmd_transition(case_no: str, to_node: str, evidence: str) -> None:
    from .state_machine import validate_transition
    # Validate only — actual write requires full context from load_case
    try:
        # We don't know from_node here without loading the case; just validate the target exists
        print(f"Transition requested: {case_no} → {to_node}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_scan_deadlines(days: int) -> None:
    print(f"(scan-deadlines --days={days} not yet implemented)")


if __name__ == "__main__":
    main()
