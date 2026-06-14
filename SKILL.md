---
name: patent-flow-skill
version: "0.1.0"
description: Patent lifecycle management for 8-node Feishu-based workflow
hosts:
  - openclaw
  - claude-code
  - codex
tools:
  - tools/load_case.sh
  - tools/transition.sh
  - tools/append_event.sh
  - tools/scan_deadlines.sh
  - tools/meta/list_skill_files.sh
  - tools/meta/read_skill_file.sh
  - tools/meta/propose_patch.sh
  - tools/meta/apply_patch.sh
  - tools/meta/run_tests.sh
hooks:
  - hooks/daily_oa_deadline.yaml
  - hooks/monthly_priority_scan.yaml
  - hooks/monthly_annuity_scan.yaml
env_required:
  - LEDGER_APP_TOKEN
  - LEDGER_MAIN_TABLE
  - LEDGER_EVENTS_TABLE
---

# Patent Flow Skill

This skill manages the full lifecycle of patent applications through an 8-node state machine backed by Feishu (Lark).

## Quickstart

```bash
pip install -e ".[dev]"
lark-cli auth login --app-id <app_id> --app-secret <secret>
export LEDGER_APP_TOKEN=...
export LEDGER_MAIN_TABLE=...
export LEDGER_EVENTS_TABLE=...
```

## Hard Rules for LLM

1. All state writes MUST go through `transition.sh` — never write to bitable or docs directly.
2. `transition` validates against `state_machine.yaml`; illegal jumps are rejected.
3. Meta patch tools (`propose_patch` / `apply_patch`) only work on the `dev` branch.
4. `apply_patch` automatically runs tests; failure triggers `git reset --hard HEAD`.
