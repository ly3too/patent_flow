#!/usr/bin/env bash
# List all source files in the skill package
find "$(git rev-parse --show-toplevel)" \
  \( -name "*.py" -o -name "*.yaml" -o -name "*.sh" -o -name "*.md" \) \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  | sort
