#!/usr/bin/env bash
# Usage: append_event.sh <case_no> <source> <event_type> <summary>
set -euo pipefail

CASE_NO="${1:?}" SOURCE="${2:?}" EVENT_TYPE="${3:?}" SUMMARY="${4:?}"

lark-cli base +record-create \
  --app-token "$LEDGER_APP_TOKEN" \
  --table-id "$LEDGER_EVENTS_TABLE" \
  --fields "{\"案号\":\"$CASE_NO\",\"来源\":\"$SOURCE\",\"事件类型\":\"$EVENT_TYPE\",\"摘要\":\"$SUMMARY\"}"
