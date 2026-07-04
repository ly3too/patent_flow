# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`patent-flow-skill` is a cross-host AI Agent skill package for automating the full lifecycle of patent applications (挖掘→查新→交底→委案→回稿→优先权→OA→授权年费). It runs on OpenClaw (production) and Claude Code (debugging/development), sharing one codebase across both hosts via live-linked skills.

Storage is entirely within Feishu (Lark): a top-level multi-dimensional table as the global index, per-case document folders in the knowledge base, and one Feishu group chat per patent case as the runtime container. Full design rationale: [design.md](design.md).

## Three-layer skill architecture

Skills live in `skills/` and are organized top-to-bottom by how independently they can be reasoned about:

```
skills/
├── workflow/patent-flow/       ← top: single orchestrator, routes events to the right task skill
├── task/patent-*/              ← middle: one skill per lifecycle node (S1..S8) + cross-cutting tasks
│                                  (patent-case-init, patent-deadline-scan, patent-self-evolve)
└── tool/patent-cli/            ← bottom: atomic lark-cli / patent_flow CLI wrappers, no business logic
```

Each skill directory has its own `SKILL.md` (frontmatter + instructions), following the same convention as the `lark-*` skills already installed on this machine. Higher layers call lower layers; lower layers never call up. All state writes funnel through `tool/patent-cli`'s `transition.sh`.

**Keeping skills live**: this repo is the source of truth. `scripts/link_skills.sh` symlinks every `skills/<layer>/<name>` directory into both `~/.claude/skills/<name>` and `~/.openclaw/skills/<name>`, so edits here take effect immediately in both hosts without any install/reload step. Re-run it after adding a new skill directory.

## Commands

System Python is 3.9 (too old). Use the Codex runtime Python:

```bash
export PYTHON=/Users/ly3too/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12

# Install dependencies
$PYTHON -m pip install -e ".[dev]"

# Run all tests
$PYTHON -m pytest

# Run a single test file
$PYTHON -m pytest tests/test_state_machine.py

# Dispatch a node handler by hand (dry run against real Feishu env)
$PYTHON -m patent_flow run-node 2026017CNU --inputs '{"ipr_verdict": "有新创性"}'

# Scan the two cron-driven nodes (S6/S8) for today's reminders
$PYTHON -m patent_flow scan-deadlines

# Lint
$PYTHON -m ruff check patent_flow/

# Run the CLI
$PYTHON -m patent_flow <cmd>

# Re-link dev skills into Claude Code + OpenClaw
bash scripts/link_skills.sh

# Install Lark CLI (Feishu API infrastructure) and authenticate
npm install -g @larksuiteoapi/lark-cli
lark-cli auth login --app-id cli_xxx --app-secret xxx
```

## Architecture

### Core Design Principle

Business logic lives only in `patent_flow/` (the core package) plus the `skills/` tree that exposes it to an LLM host. The host (OpenClaw / Claude Code) is a thin shell that loads skills via `SKILL.md`. This means the host can be swapped with zero business logic changes.

### State Machine (`patent_flow/state_machine.yaml`)

The 8-node pipeline is **YAML-defined with Python guard functions** — the LLM cannot skip nodes or make illegal transitions. All state writes go through a single `transition()` function that atomically syncs four places: the case master document (`agent:state` block) → the Bitable master table → the group chat announcement + name → a broadcast message.

Nodes: `S1_mining → S2_search → S3_disclosure → S4_filing → S5_review → S6_priority_watch → S7_oa → S8_annuity → DONE` (with `TERMINATED` exit from S2). Node business logic lives in `patent_flow/nodes/`, one module per node — each corresponds 1:1 to a `skills/task/patent-*` skill. Handlers are pure decision functions: `run(case, **inputs) -> NodeResult` (`patent_flow/nodes/base.py`). They never touch `lark-cli` or call `transition()` directly; `to_node=None` means "stay put, still waiting on a human_gate or a deadline that hasn't hit yet."

`patent_flow/registry.py` maps state names to their handler's `run`. `patent_flow/workflow.py` is the orchestrator: `identify_case()` (chat_id → 案号), `dispatch()` (routes to the registry, then re-validates any proposed `to_node` against the state machine before anything downstream runs), `apply_result()` (only calls `transition()` when `to_node` is set), and `scan_deadlines()` (the S6/S8 cron entry point — iterates every case on those two nodes and dispatches with no `pm_decision`, so each handler only returns a reminder or stays silent).

### Storage Topology

Everything except the group chat lives inside one Feishu Wiki space: `patent_flow` itself is the root (`$PATENT_FLOW_ROOT_TOKEN` = that space's `space_id`), not a node nested under some other space. Nothing patent-related should be created as a parallel top-level resource outside this space, and — this was a real bug found during the first live case-init run — nothing should end up in anyone's personal Drive ("我的空间") either; every write needs an explicit wiki space/parent-node target.

**Wiki nodes have no `folder` obj_type** (`doc/sheet/bitable/mindnote/docx/file/slides` only — verified against the real API, not assumed). "Directories" are simulated with plain `docx` nodes used purely as parents (e.g. a `cases` node, a `cases/2026` node under it); a case's main document is itself the leaf node, not a separate file inside a folder. Existing Drive documents get moved in with `wiki +move --obj-type docx --obj-token <token> --target-space-id <space_id> --target-parent-token <parent_node_token>` rather than recreated. Per-case binary attachments (scanned PDFs, etc.) attach directly to that case's node via `drive +upload --wiki-token <node_token>`.

```
patent_flow (Wiki space, IS the root — $PATENT_FLOW_ROOT_TOKEN = space_id)
├── 专利总台账.bitable          ← global index + status board (3 tables: 案件主表, 事件流水, 待办截止)
├── templates (docx node, parent-only placeholder)
│    └── 案件主文档模板.docx (child node)
└── cases (docx node, parent-only placeholder)
     └── YYYY (docx node, parent-only placeholder)
          └── <案号> - <案件名>     ← the case's own node IS 00_案件主文档; Agent reads/writes agent:state / agent:elements / agent:log HTML comment blocks

群「[案号] 案件名 - 节点」            ← runtime container (IM object, not part of the wiki tree); chat ID ↔ case number is 1-to-1
```

The master document uses HTML comment delimiters (`<!-- agent:state:begin -->` … `<!-- agent:state:end -->`) so humans and the Agent can co-edit the same doc without conflicts.

### Tool Layer (`tools/`, exposed via `skills/tool/patent-cli`)

Shell scripts are thin wrappers over `lark-cli` and `python -m patent_flow` commands. `tools/run_node.sh <案号> <inputs_json>` is the main entry point — it dispatches the case's current-node handler and applies the result in one call. `tools/transition.sh <案号> <to_node> <evidence>` bypasses the node handler for exceptional manual corrections (still guarded by the state machine). The `meta/` subdirectory contains self-introspection tools (`read_skill_file`, `propose_patch`, `apply_patch`, `run_tests`) that allow the Agent to safely modify its own Skill code under a two-branch + test-gate guard: Agent writes only to `dev` branch; a passing `pytest` run is required before any patch applies; human merges `dev → main` to activate. Exposed to conversation as `skills/task/patent-self-evolve`.

### Agent Decision Loop

Trigger (Feishu callback / cron / card button) → `skills/workflow/patent-flow` identifies the case (group ID ↔ case number is 1:1, `workflow.identify_case()`) → loads master doc agent blocks + recent events via `tool/patent-cli` → LLM reads the `task/patent-*` skill matching the current node and gathers the structured inputs that node's handler needs → `tools/run_node.sh` (`workflow.dispatch()` + `apply_result()`) → four-way atomic sync if a legal transition was decided → next wakeup deadline registered (S6/S8 fall back to the daily `hooks/daily_deadline_scan.yaml` cron regardless).

The LLM is treated as stateless on every invocation; the master document is the complete context handed to it each time.

### Feishu Infrastructure

All Feishu API calls go through `lark-cli` (official open-source, MIT, 2500+ APIs). Direct SDK calls are not used. `patent_flow/store.py` wraps `lark-cli` subcommands: `drive`, `docs`, `im`, `base`.

### Automation Priority

P1 (implement first — fully automatic): S4 委案, S6 优先权, S8 年费
P2 (AI-assisted): S1 挖掘, S2 查新, S7 OA
P3 (lower AI density): S3 交底, S5 回稿
