---
name: patent-priority-watch
version: "0.1.0"
layer: task
description: "专利 S6 优先权监听节点任务：全自动，每日 cron 扫描台账中临近优先权到期（申请日+10个月）的案件，命中 60/30/14 天提醒档位时生成 PM 决策卡片（申请美国/欧洲/都申请/放弃），回填后流转到 S7 OA。当案件当前节点为 S6_priority_watch，或每日 cron 触发时使用。落地优先级 P1。不负责回稿（[patent-review](../patent-review/SKILL.md)）。"
metadata:
  node: S6_priority_watch
  handler: patent_flow/nodes/s6_priority.py
  human_gate: pm_priority_decision
  triggers: [cron_daily, ten_month_due]
  parallel_to: [S7_oa]
  on_complete: [S7_oa]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-priority-watch（task 层：S6 优先权监听，P1 全自动）

design.md 第十一节标注为 **P1 全自动**节点。与 S7 OA 并行运行，互不阻塞。

## 触发场景

```
(10 个月后某天 9:00, Agent 自动在群里发)
Bot: ⏰ @PM 优先权决策提醒
     距优先权到期: 2 个月
     产品销量摘要: ...
     [申请美国] [申请欧洲] [都申请] [放弃]
```

## 催办节奏（可对话式调整，见 [patent-self-evolve](../patent-self-evolve/SKILL.md)）

`patent_flow/nodes/s6_priority.py` 中的 `REMIND_DAYS = [60, 30, 14]`：优先权到期前恰好 60/30/14 天当天各催办一次（精确天数匹配，不是"≤N天都提醒"），`ESCALATE_AT = 14` 即 14 天档同时升级 @leader。到期日 = 申请日 + 10 个月（`patent_flow/nodes/s6_priority.priority_deadline()`）。

## 执行步骤

1. `hooks/daily_deadline_scan.yaml` 每日 9:00 触发 `tools/scan_deadlines.sh` → `patent_flow.workflow.scan_deadlines()`，对本节点的每个案件调用 `s6_priority.run(case, today)`（不传 `pm_decision`）
2. 命中提醒档位（`needs_human=True`）的案件生成 PM 决策卡片；未命中的案件本次静默跳过
3. PM 点击卡片回填决策后（`human_gate: pm_priority_decision`）→ `tools/run_node.sh <案号> '{"pm_decision": "申请美国"}'`（或 `申请欧洲`/`都申请`/`放弃`），内部即 `s6_priority.run(case, today, pm_decision=...)` 返回 `to_node=S7_oa` 并自动 `transition()`

## 完成后

移交 [patent-oa](../patent-oa/SKILL.md)（S7 OA）。
