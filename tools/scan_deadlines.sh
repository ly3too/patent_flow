#!/usr/bin/env bash
# Scan bitable for S6/S8 cases due a reminder today (per-node REMIND_DAYS tiers).
set -euo pipefail

python -m patent_flow scan-deadlines
