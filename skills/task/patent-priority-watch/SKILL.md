---
name: patent-priority-watch
version: "0.1.0"
layer: task
description: "专利 S6 优先权监听节点任务：全自动，每月定时扫描台账中临近优先权到期（申请日+10个月）的案件，生成 PM 决策卡片（申请美国/欧洲/都申请/放弃），回填后流转到 S7 OA。当案件当前节点为 S6_priority_watch，或月度 cron / 台账自动化 webhook 触发时使用。落地优先级 P1。不负责回稿（[patent-review](../patent-review/SKILL.md)）。"
metadata:
  node: S6_priority_watch
  handler: patent_flow/nodes/s6_priority.py
  human_gate: pm_priority_decision
  triggers: [cron_monthly, ten_month_due]
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

`patent_flow/nodes/s6_priority.py` 中的 `REMIND_DAYS = [60, 30, 14]`：优先权到期前 60/30/14 天各催办一次，14 天仍未回填则升级 @leader。

## 执行步骤

1. `tools/scan_deadlines.sh` 或 `hooks/monthly_priority_scan.yaml` 定时触发扫描
2. 对临近到期案件生成 PM 决策卡片
3. PM 点击卡片回填决策后（`human_gate: pm_priority_decision`）→ `transition.sh <案号> S7_oa <决策依据>`

## 完成后

移交 [patent-oa](../patent-oa/SKILL.md)（S7 OA）。
