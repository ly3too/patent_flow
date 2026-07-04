#!/usr/bin/env bash
# Usage: read_skill_file.sh <relative_path>
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cat "$ROOT/${1:?Usage: read_skill_file.sh <path>}"
