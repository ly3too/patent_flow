#!/usr/bin/env bash
# Scan bitable for cases with deadline within N days (default 3)
set -euo pipefail

DAYS="${1:-3}"
python -m patent_flow scan-deadlines --days "$DAYS"
