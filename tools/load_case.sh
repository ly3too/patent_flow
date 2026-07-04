#!/usr/bin/env bash
# Usage: load_case.sh <case_no>
# Returns case state JSON from bitable + agent:state block from master doc
set -euo pipefail

CASE_NO="${1:?Usage: load_case.sh <case_no>}"

lark-cli base +query \
  --app-token "$LEDGER_APP_TOKEN" \
  --table-id "$LEDGER_MAIN_TABLE" \
  --filter "CurrentValue.[案号] = \"$CASE_NO\""
