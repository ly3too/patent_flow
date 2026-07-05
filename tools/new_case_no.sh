#!/usr/bin/env bash
# Generates a new case number: YYYYMMDD + 5 random uppercase letters,
# retried against the live ledger on collision.
set -euo pipefail

python -m patent_flow new-case-no
