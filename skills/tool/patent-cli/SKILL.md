---
name: patent-cli
version: "0.1.0"
layer: tool
description: "专利流程底层工具命令层：load_case / transition / append_event / scan_deadlines 等原子操作，全部是对 lark-cli 和 patent_flow CLI 的薄壳封装。不做业务判断，只做单次读写。当上层 task/workflow skill 需要读取案件状态、执行状态跳转、写事件流水、扫描截止日期，或需要自省/受控修改 Skill 自身代码时调用。不负责节点业务逻辑（那是 task 层）和多节点编排（那是 workflow 层）。"
metadata:
  requires:
    bins: ["lark-cli", "python", "git", "pytest"]
  env_required:
    - LEDGER_APP_TOKEN
    - LEDGER_MAIN_TABLE
    - LEDGER_EVENTS_TABLE
  tools:
    - ../../../tools/load_case.sh
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
| `tools/transition.sh <案号> <目标节点> <依据>` | 状态机守卫校验 + 触发 `python -m patent_flow transition` | `patent_flow.transition.transition()` |
| `tools/append_event.sh <案号> <来源> <事件类型> <摘要>` | 写事件流水（append-only） | `lark-cli base +record-create` |
| `tools/scan_deadlines.sh [天数]` | 扫描台账中临近截止的案件 | `python -m patent_flow scan-deadlines` |

## 自省 / 受控自改工具（meta/）

| 命令 | 用途 |
|---|---|
| `tools/meta/list_skill_files.sh` | 列出本仓库全部源码文件 |
| `tools/meta/read_skill_file.sh <路径>` | 读取指定源码文件 |
| `tools/meta/propose_patch.sh <patch文件>` | 展示 diff，不落盘，等待人工批准 |
| `tools/meta/apply_patch.sh <patch文件>` | 应用 patch → 跑 `pytest` → 失败则 `git reset --hard`；只允许在 `dev` 分支执行 |
| `tools/meta/run_tests.sh` | 运行全部测试 |

## 硬规则

1. **唯一写入口**：任何状态变更必须走 `transition.sh`，它内部调用 `patent_flow.state_machine.validate_transition()` 做守卫校验，非法跳转直接抛错。
2. **先写事件流水，后写主表/群**：保证审计可追溯，即使后续步骤失败也不会丢事件。
3. `apply_patch.sh` 只能在 `dev` 分支运行；测试失败自动 `git reset --hard HEAD`。
4. 环境变量 `LEDGER_APP_TOKEN` / `LEDGER_MAIN_TABLE` / `LEDGER_EVENTS_TABLE` 必须在调用前配置好（参考 [lark-shared](../../../../../.agents/skills/lark-shared/SKILL.md) 做 `lark-cli auth login`）。
