#!/usr/bin/env bash
# Scan bitable for S6/S8 cases due a reminder today (per-node REMIND_DAYS tiers).
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.patent_flow"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

"${PYTHON:-python3}" -m patent_flow scan-deadlines
