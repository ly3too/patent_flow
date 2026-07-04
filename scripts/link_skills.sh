#!/usr/bin/env bash
# Symlink every skills/<layer>/<name> directory in this repo into the Claude
# Code and OpenClaw user-level skill directories, so edits made here take
# effect immediately in both hosts without any install/reload step.
#
# Idempotent: safe to re-run after adding/removing a skill directory.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_ROOT="$REPO_ROOT/skills"

TARGET_DIRS=(
  "$HOME/.claude/skills"
  "$HOME/.openclaw/skills"
)

link_one() {
  local src="$1" target_dir="$2" name
  name="$(basename "$src")"
  local dest="$target_dir/$name"

  mkdir -p "$target_dir"

  if [[ -L "$dest" ]]; then
    if [[ "$(readlink "$dest")" == "$src" ]]; then
      echo "  = $dest (already linked)"
      return
    fi
    echo "  ! $dest points elsewhere, relinking"
    rm "$dest"
  elif [[ -e "$dest" ]]; then
    echo "  x $dest exists and is not a symlink — skipping (resolve manually)" >&2
    return
  fi

  ln -s "$src" "$dest"
  echo "  + $dest -> $src"
}

for target_dir in "${TARGET_DIRS[@]}"; do
  echo "== linking into $target_dir =="
  for layer_dir in "$SKILLS_ROOT"/*/; do
    for skill_dir in "$layer_dir"*/; do
      [[ -f "$skill_dir/SKILL.md" ]] || continue
      link_one "${skill_dir%/}" "$target_dir"
    done
  done
done

echo "Done. Skills are live-linked from $SKILLS_ROOT"
