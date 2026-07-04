---
name: patent-flow
version: "0.1.0"
layer: workflow
description: "专利全生命周期工作流总入口（顶层编排 Skill）。任何在'一案一群'里 @bot 的消息、卡片回调，或 cron/台账自动化触发，都先经过这里：反查案号 → 读取案件状态（主文档 agent:state 区块 + 最近事件）→ 根据当前节点路由到对应的 task 层 skill → 校验状态机合法性 → 通过 patent-cli 原子写入同步主文档/台账/群。当消息来自专利案件群，或需要判断'现在该做什么'时最先使用本 skill 做路由决策；具体某个节点的业务逻辑不在这里做，而是委托给对应 task skill。"
metadata:
  requires:
    skills:
      - "../../tool/patent-cli/SKILL.md"
      - "../../task/patent-case-init/SKILL.md"
      - "../../task/patent-mining/SKILL.md"
      - "../../task/patent-search/SKILL.md"
      - "../../task/patent-disclosure/SKILL.md"
      - "../../task/patent-filing/SKILL.md"
      - "../../task/patent-review/SKILL.md"
      - "../../task/patent-priority-watch/SKILL.md"
      - "../../task/patent-oa/SKILL.md"
      - "../../task/patent-grant-annuity/SKILL.md"
      - "../../task/patent-deadline-scan/SKILL.md"
      - "../../task/patent-self-evolve/SKILL.md"
  state_machine: patent_flow/state_machine.yaml
---

# patent-flow（workflow 层：总编排）

这是三层 Skill 体系的**顶层入口**，对应 design.md 第七节「Agent 唤醒与决策流程」。三层结构：

```
workflow/patent-flow          ← 你在这里：读状态 + 路由决策
   │
   ├─ task/patent-case-init          （新案件）
   ├─ task/patent-mining             （S1）
   ├─ task/patent-search             （S2）
   ├─ task/patent-disclosure         （S3）
   ├─ task/patent-filing             （S4，P1 全自动）
   ├─ task/patent-review             （S5）
   ├─ task/patent-priority-watch     （S6，P1 全自动）
   ├─ task/patent-oa                 （S7）
   ├─ task/patent-grant-annuity      （S8，P1 全自动）
   ├─ task/patent-deadline-scan      （跨节点期限兜底）
   ├─ task/patent-self-evolve        （对话式自我进化）
   │
   └─ tool/patent-cli                （最底层：原子读写命令，被以上所有 task 调用）
```

## 决策流程（design.md 图七）

```
飞书事件 / Cron / 卡片回调
  → identify_case（群 ID 反查案号，一案一群 1:1 映射）
  → load_case（tool/patent-cli 的 load_case.sh：读主文档 + 最近 20 条事件）
  → compose_prompt（注入状态 + 可用工具 + 硬规则）
  → 路由到对应 task skill 做业务决策
  → transition() 守卫（tool/patent-cli 的 transition.sh，状态机校验非法跳转）
  → 合法：三处同步（主文档 + 台账 + 群公告/群名/播报）
  → 非法：拒绝并报警
  → 注册下一次唤醒（deadline）
```

## 节点 → task skill 路由表

| 当前节点 | 路由到 |
|---|---|
| （案件不存在） | [patent-case-init](../../task/patent-case-init/SKILL.md) |
| S1_mining | [patent-mining](../../task/patent-mining/SKILL.md) |
| S2_search | [patent-search](../../task/patent-search/SKILL.md) |
| S3_disclosure | [patent-disclosure](../../task/patent-disclosure/SKILL.md) |
| S4_filing | [patent-filing](../../task/patent-filing/SKILL.md) |
| S5_review | [patent-review](../../task/patent-review/SKILL.md) |
| S6_priority_watch | [patent-priority-watch](../../task/patent-priority-watch/SKILL.md) |
| S7_oa | [patent-oa](../../task/patent-oa/SKILL.md) |
| S8_annuity | [patent-grant-annuity](../../task/patent-grant-annuity/SKILL.md) |
| cron / 台账自动化触发，节点未知 | [patent-deadline-scan](../../task/patent-deadline-scan/SKILL.md) |
| 用户要求修改本 Skill 行为 | [patent-self-evolve](../../task/patent-self-evolve/SKILL.md) |

完整流转图见 [state_machine.yaml](../../../patent_flow/state_machine.yaml) 和 [design.md](../../../design.md) 第五节。

## 意图识别分档（design.md 6.4，避免打扰）

| 触发方式 | 处理 | 是否调用本 workflow |
|---|---|---|
| @bot + 命令（如 `@bot status`） | 正则本地解析 | 否，直接走 tool 层 |
| @bot + 自然语言 | LLM function calling | 是 |
| 群内文件上传 / 关键事件 | LLM 自动归档 + 询问 | 是 |
| 普通聊天（人和人讨论） | 不响应，仅记录 | 否 |

## 硬规则（不可绕过）

1. **状态机是唯一真相**：无论 LLM 怎么"想", 都不能跳出 `patent_flow/state_machine.yaml` 定义的 `on_complete` 图。所有写操作必须走 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `transition.sh`。
2. **LLM 无状态**：每次唤醒都当新员工，把主文档（病历本）完整递给它，不依赖对话历史记忆。
3. **三层各司其职**：workflow 只做路由和状态机守卫，业务细节在 task 层，飞书 API 调用细节在 tool 层——禁止跨层跳过（例如 workflow 直接拼 `lark-cli` 参数）。
4. **一案一群**：群 ID ↔ 案号一一映射，不需要额外的 identify_case 逻辑，直接用群 ID 反查台账。
