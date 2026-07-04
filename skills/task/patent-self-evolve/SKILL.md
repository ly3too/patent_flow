---
name: patent-self-evolve
version: "0.1.0"
layer: task
description: "对话式自我进化任务：让 Agent 安全地读取并修改 patent-flow-skill 自身源码（业务逻辑参数、节点 handler、状态机定义等）。当用户在对话中要求调整本 Skill 的行为（如'催办间隔改成3天'、'S2查新加一步XX检查'）时使用。只能操作 dev 分支，且必须先过 pytest 才能提交；不负责具体案件的业务处理（那是其它 task skill）。"
metadata:
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
  guardrails:
    - "测试必须先过：apply_patch 后自动跑 pytest，失败立即 git reset --hard HEAD"
    - "双分支：只能改 dev 分支，人工 merge 到 main 后 openclaw skills reload 才生效"
---

# patent-self-evolve（task 层：自省 + 受控编辑）

对应 design.md 第十节「对话式自我进化」。

## 三个能力

1. **自省 Introspect**：`tools/meta/list_skill_files.sh` / `tools/meta/read_skill_file.sh` 读取自身源码
2. **受控编辑 Patch**：生成 diff 后用 `tools/meta/propose_patch.sh` 展示给用户，用户明确同意后再 `tools/meta/apply_patch.sh` 落盘
3. **版本化 Git**：每次 `apply_patch` 自动 commit 到 `dev` 分支，可随时 `git revert`

## 对话样例

```
你: S6 的催办间隔太长了, PM 都不看, 改成 3 天一次

Agent: 好, 我先看一下当前实现。
       [read_skill_file patent_flow/nodes/s6_priority.py]

       现在是 REMIND_DAYS = [60, 30, 14]。我打算改成:
       REMIND_DAYS = [14, 7, 3, 1]，并在最后一次同时升级到 leader。

       diff:
       - REMIND_DAYS = [60, 30, 14]
       + REMIND_DAYS = [14, 7, 3, 1]
       + ESCALATE_AT = 1

       要不要 apply?

你: apply

Agent: [apply_patch] [run_tests → N passed]
       已 commit (dev 分支)。等你在 OpenClaw 那边 merge 到 main 就生效。
```

## 硬规则

- 绝不直接在 `main` 分支上跑 `apply_patch.sh`（`tools/meta/apply_patch.sh` 会拒绝非 `dev` 分支）。
- 每次 patch 必须先经用户在对话中明确说"apply"/"同意"才能落盘。
