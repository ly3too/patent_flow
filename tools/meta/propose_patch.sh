#!/usr/bin/env bash
# Usage: propose_patch.sh <patch_file>
# Displays the diff without applying it; requires human approval before apply_patch.sh
set -euo pipefail
git diff --stat
cat "${1:?Usage: propose_patch.sh <patch_file>}"
