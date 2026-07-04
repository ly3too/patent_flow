---
name: patent-cli
version: "0.1.0"
layer: tool
description: "专利流程底层工具命令层：load_case / run_node / transition / append_event / scan_deadlines 等原子操作，全部是对 lark-cli 和 patent_flow CLI 的薄壳封装。不做业务判断，只做单次读写。当上层 task/workflow skill 需要读取案件状态、派发节点决策、执行状态跳转、写事件流水、扫描截止日期，或需要自省/受控修改 Skill 自身代码时调用。不负责节点业务逻辑（那是 task 层的 patent_flow/nodes/*.py）和多节点编排（那是 workflow 层的 patent_flow/workflow.py）。"
metadata:
  requires:
    bins: ["lark-cli", "python", "git", "pytest"]
  env_required:
    - LEDGER_APP_TOKEN
    - LEDGER_MAIN_TABLE
    - LEDGER_EVENTS_TABLE
  tools:
    - ../../../tools/load_case.sh
    - ../../../tools/run_node.sh
    - ../../../tools/transition.sh
    - ../../../tools/append_event.sh
    - ../../../tools/scan_deadlines.sh
    - ../../../tools/meta/list_skill_files.sh
    - ../../../tools/meta/read_skill_file.sh
    - ../../../tools/meta/propose_patch.sh
    - ../../../tools/meta/apply_patch.sh
    - ../../../tools/meta/run_tests.sh
---

# patent-cli（工具层）

这是三层 Skill 体系的最底层：**只暴露原子命令，不做任何业务判断**。task 层和 workflow 层都应该通过这里的命令读写飞书，而不是自己拼 `lark-cli` 参数。

## 命令一览

| 命令 | 用途 | 对应实现 |
|---|---|---|
| `tools/load_case.sh <案号>` | 读取案件主表记录 | `lark-cli base +query` |
| `tools/run_node.sh <案号> <inputs_json>` | **派发当前节点的业务判断**：调用 `patent_flow/registry.py` 找到当前节点 handler，传入结构化输入（三要素草稿、IPR 判定等），拿到 `NodeResult` 后自动 `transition()`（若有合法 `to_node`） | `patent_flow.workflow.dispatch()` + `apply_result()` |
| `tools/transition.sh <案号> <目标节点> <依据>` | 不经节点 handler、直接指定目标节点做状态跳转（用于人工纠错或跳过节点判断的场景），仍受状态机守卫校验 | `patent_flow.workflow.apply_result()` |
| `tools/append_event.sh <案号> <来源> <事件类型> <摘要>` | 写事件流水（append-only） | `lark-cli base +record-create` |
| `tools/scan_deadlines.sh` | 扫描 S6/S8 两个 cron 驱动节点，返回今天命中提醒档位的案件 | `patent_flow.workflow.scan_deadlines()` |

> `transition.sh` / `run_node.sh` 的 `--chat-id` / `--doc-token` / `--state-block-id` / `--case-title` 均为可选：不传时自动取案件记录里的 `群ID` / `案件主文档` 字段（`--state-block-id` 默认 `agent_state`，`--case-title` 默认案号）。多数场景应优先用 `run_node.sh`——业务判断和状态跳转在一次调用里原子完成；`transition.sh` 仅用于绕过节点 handler 的例外情况。

## 自省 / 受控自改工具（meta/）

| 命令 | 用途 |
|---|---|
| `tools/meta/list_skill_files.sh` | 列出本仓库全部源码文件 |
| `tools/meta/read_skill_file.sh <路径>` | 读取指定源码文件 |
| `tools/meta/propose_patch.sh <patch文件>` | 展示 diff，不落盘，等待人工批准 |
| `tools/meta/apply_patch.sh <patch文件>` | 应用 patch → 跑 `pytest` → 失败则 `git reset --hard`；只允许在 `dev` 分支执行 |
| `tools/meta/run_tests.sh` | 运行全部测试 |

## 硬规则

1. **唯一写入口**：任何状态变更必须走 `run_node.sh` 或 `transition.sh`，两者最终都落到 `patent_flow.transition.transition()`，内部调用 `state_machine.validate_transition()` 做守卫校验，非法跳转直接抛错（`dispatch()` 在拿到节点 handler 的决策后也会先校验一次，双重保险）。
2. **先写事件流水，后写主表/群**：保证审计可追溯，即使后续步骤失败也不会丢事件。
3. `apply_patch.sh` 只能在 `dev` 分支运行；测试失败自动 `git reset --hard HEAD`。
4. 环境变量 `LEDGER_APP_TOKEN` / `LEDGER_MAIN_TABLE` / `LEDGER_EVENTS_TABLE` 必须在调用前配置好（参考 [lark-shared](../../../../../.agents/skills/lark-shared/SKILL.md) 做 `lark-cli auth login`）。
