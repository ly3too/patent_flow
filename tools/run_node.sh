#!/usr/bin/env bash
# Usage: run_node.sh <case_no> <inputs_json>
# Dispatches the case's current-node handler (patent_flow/registry.py) with
# structured inputs gathered by the calling LLM, then applies the result
# (transition() only fires if the handler decided a legal to_node).
set -euo pipefail

CASE_NO="${1:?Usage: run_node.sh <case_no> <inputs_json>}"
INPUTS="${2:-{\}}"

python -m patent_flow run-node "$CASE_NO" --inputs "$INPUTS"
