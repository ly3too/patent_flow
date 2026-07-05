#!/usr/bin/env bash
# Usage: load_case.sh <case_no>
# Returns case state JSON from bitable + agent:state block from master doc
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.patent_flow"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

CASE_NO="${1:?Usage: load_case.sh <case_no>}"

lark-cli base +record-list \
  --base-token "$LEDGER_APP_TOKEN" \
  --table-id "$LEDGER_MAIN_TABLE" \
  --filter-json "{\"logic\":\"and\",\"conditions\":[[\"案号\",\"==\",\"$CASE_NO\"]]}" \
  --format json
