#!/usr/bin/env bash
# Usage: apply_patch.sh <patch_file>
# Applies patch to dev branch, runs tests; hard-resets on failure.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
PATCH="${1:?Usage: apply_patch.sh <patch_file>}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [[ "$BRANCH" != "dev" ]]; then
  echo "ERROR: apply_patch must run on the dev branch (current: $BRANCH)" >&2
  exit 1
fi

git apply "$PATCH"

if ! bash "$ROOT/tools/meta/run_tests.sh"; then
  echo "Tests failed — reverting patch" >&2
  git reset --hard HEAD
  exit 1
fi

git add -A
git commit -m "skill: apply agent patch $(date -u +%Y%m%dT%H%M%SZ)"
echo "Patch applied and committed on dev branch."
