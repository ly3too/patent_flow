# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`patent-flow-skill` is a cross-host AI Agent skill package for automating the full lifecycle of patent applications (挖掘→查新→交底→委案→回稿→优先权→OA→授权年费). It runs on OpenClaw (production), Claude Code (debugging), and Codex CLI (testing), sharing one codebase across all three hosts.

Storage is entirely within Feishu (Lark): a top-level multi-dimensional table as the global index, per-case document folders in the knowledge base, and one Feishu group chat per patent case as the runtime container.

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

# Run a single test
$PYTHON -m pytest tests/test_state_machine.py::test_illegal_transition

# Lint
$PYTHON -m ruff check patent_flow/

# Run the CLI
$PYTHON -m patent_flow <cmd>

# Install Lark CLI (Feishu API infrastructure)
npm install -g @larksuiteoapi/lark-cli

# Authenticate Lark CLI
lark-cli auth login --app-id cli_xxx --app-secret xxx
```

## Architecture

### Core Design Principle

Business logic lives only in `patent_flow/` (the Skill package). The host (OpenClaw / Claude Code / Codex) is a thin shell that loads the Skill via `SKILL.md`. This means host can be swapped with zero business logic changes.

### State Machine (`patent_flow/state_machine.yaml`)

The 8-node pipeline is **YAML-defined with Python guard functions** — the LLM cannot skip nodes or make illegal transitions. All state writes go through a single `transition()` function that atomically syncs four places: the case master document (`agent:state` block) → the Bitable master table → the group chat announcement + name → a broadcast message.

Nodes: `S1_mining → S2_search → S3_disclosure → S4_filing → S5_review → S6_priority_watch → S7_oa → S8_annuity → DONE` (with `TERMINATED` exit from S2).

### Storage Topology

```
Feishu Tenant
├── 专利总台账.bitable          ← global index + status board (3 tables: 案件主表, 事件流水, 待办截止)
├── 知识库/YYYY/<案号>/         ← per-case folder with numbered documents
│    └── 00_案件主文档.docx     ← single source of truth; Agent reads/writes agent:state / agent:elements / agent:log HTML comment blocks
└── 群「[案号] 案件名 - 节点」  ← runtime container; chat ID ↔ case number is 1-to-1
```

The master document uses HTML comment delimiters (`<!-- agent:state:begin -->` … `<!-- agent:state:end -->`) so humans and the Agent can co-edit the same doc without conflicts.

### Tool Layer (`tools/`)

Shell scripts are thin wrappers over `lark-cli` commands, exposed to the LLM as function-calling tools. The `meta/` subdirectory contains self-introspection tools (`read_skill_file`, `propose_patch`, `apply_patch`, `run_tests`) that allow the Agent to safely modify its own Skill code under a two-branch + test-gate guard: Agent writes only to `dev` branch; a passing `pytest` run is required before any patch applies; human merges `dev → main` to activate.

### Agent Decision Loop

Trigger (Feishu callback / cron / card button) → `load_case` (read master doc agent blocks + recent events) → `compose_prompt` (inject state + tools + hard rules) → LLM function calling → `transition()` guard → four-way atomic sync → `set_deadline` (register next wakeup).

The LLM is treated as stateless on every invocation; the master document is the complete context handed to it each time.

### Feishu Infrastructure

All Feishu API calls go through `lark-cli` (official open-source, MIT, 2500+ APIs). Direct SDK calls are not used. The `store.py` module wraps `lark-cli` subcommands: `drive`, `docs`, `im`, `base`.

### Automation Priority

P1 (implement first — fully automatic): S4 委案, S6 优先权, S8 年费  
P2 (AI-assisted): S1 挖掘, S2 查新, S7 OA  
P3 (lower AI density): S3 交底, S5 回稿
