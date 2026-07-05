#!/usr/bin/env bash
# Usage: run_node.sh <case_no> <inputs_json>
# Dispatches the case's current-node handler (patent_flow/registry.py) with
# structured inputs gathered by the calling LLM, then applies the result
# (transition() only fires if the handler decided a legal to_node).
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.patent_flow"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

CASE_NO="${1:?Usage: run_node.sh <case_no> <inputs_json>}"
INPUTS="${2:-{\}}"

"${PYTHON:-python3}" -m patent_flow run-node "$CASE_NO" --inputs "$INPUTS"
