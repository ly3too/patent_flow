#!/usr/bin/env bash
# Generates a new case number: YYYYMMDD + 5 random uppercase letters,
# retried against the live ledger on collision.
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.patent_flow"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

"${PYTHON:-python3}" -m patent_flow new-case-no
