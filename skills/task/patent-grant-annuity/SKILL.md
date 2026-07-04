---
name: patent-grant-annuity
version: "0.1.0"
layer: task
description: "专利 S8 授权年费节点任务：全自动，每日 cron 监控年费到期日，命中 90/30/7 天提醒档位时生成 PM 维持决策卡片，回填后生成缴费指令邮件草稿发给代理所，完成后流转到 DONE 归档。当案件当前节点为 S8_annuity，或每日 cron 触发时使用。落地优先级 P1，是流程终点前的最后一步。不负责 OA 答复（[patent-oa](../patent-oa/SKILL.md)）。"
metadata:
  node: S8_annuity
  handler: patent_flow/nodes/s8_annuity.py
  human_gate: pm_maintain_decision
  triggers: [cron_daily, annuity_due]
  on_complete: [DONE]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-grant-annuity（task 层：S8 授权年费，P1 全自动）

design.md 第十一节标注为 **P1 全自动**节点。

## 催办节奏（可对话式调整，见 [patent-self-evolve](../patent-self-evolve/SKILL.md)）

`patent_flow/nodes/s8_annuity.py` 中的 `REMIND_DAYS = [90, 30, 7]`：年费到期前恰好 90/30/7 天当天各催办一次（精确天数匹配），`ESCALATE_AT = 7` 即 7 天档同时升级 @leader。

## 执行步骤

1. 归档授权证书到 `08_授权证书.pdf`，写入台账「年费到期日」字段
2. `hooks/daily_deadline_scan.yaml` 每日 9:00 触发 `tools/scan_deadlines.sh` → `s8_annuity.run(case, today)`（不传 `pm_decision`），命中提醒档位才生成 PM 维持决策卡片，否则静默跳过
3. PM 回填决策 → `tools/run_node.sh <案号> '{"pm_decision": "继续缴费"}'`（或 `"放弃维持"`），内部即 `s8_annuity.run(case, today, pm_decision=...)`：
   - 继续缴费 → 返回 `to_node=DONE` + 缴费指令邮件草稿（`extra["payment_email_draft"]`），自动 `transition()`，发给代理所
   - 放弃维持 → 返回 `to_node=DONE`，专利终止维持

## 完成后

案件进入 `DONE` 终态（design.md 5.1 流转图）。年费监控在案件专利有效期内持续存在，由 `hooks/daily_deadline_scan.yaml` 逐年唤起（每次到期前的 90/30/7 天档）。
