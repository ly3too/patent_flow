#!/usr/bin/env bash
# Usage: transition.sh <case_no> <to_node> <evidence>
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.patent_flow"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

CASE_NO="${1:?}"
TO_NODE="${2:?}"
EVIDENCE="${3:-}"

"${PYTHON:-python3}" -m patent_flow transition "$CASE_NO" "$TO_NODE" --evidence "$EVIDENCE"
