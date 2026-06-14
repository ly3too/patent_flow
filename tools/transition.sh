#!/usr/bin/env bash
# Usage: transition.sh <case_no> <to_node> <evidence>
set -euo pipefail

CASE_NO="${1:?}"
TO_NODE="${2:?}"
EVIDENCE="${3:-}"

python -m patent_flow transition "$CASE_NO" "$TO_NODE" --evidence "$EVIDENCE"
