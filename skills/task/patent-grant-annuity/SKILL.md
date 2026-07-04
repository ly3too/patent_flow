---
name: patent-grant-annuity
version: "0.1.0"
layer: task
description: "专利 S8 授权年费节点任务：全自动，监控授权/年费到期日，生成 PM 维持决策卡片，回填后生成缴费指令邮件草稿发给代理所，完成后流转到 DONE 归档。当案件当前节点为 S8_annuity，或年费到期 cron 触发时使用。落地优先级 P1，是流程终点前的最后一步。不负责 OA 答复（[patent-oa](../patent-oa/SKILL.md)）。"
metadata:
  node: S8_annuity
  handler: patent_flow/nodes/s8_annuity.py
  human_gate: pm_maintain_decision
  triggers: [annuity_due]
  on_complete: [DONE]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-grant-annuity（task 层：S8 授权年费，P1 全自动）

design.md 第十一节标注为 **P1 全自动**节点。

## 执行步骤

1. 归档授权证书到 `08_授权证书.pdf`，写入台账「年费到期日」字段
2. `hooks/monthly_annuity_scan.yaml` 定时扫描年费临近到期（90 天内）的案件
3. 生成 PM 维持决策卡片（继续缴费 / 放弃维持）
4. PM 回填决策（`human_gate: pm_maintain_decision`）：
   - 继续缴费 → 生成缴费指令邮件草稿发给代理所，`transition.sh <案号> DONE "本年度年费已缴"`（次年度到期前会再次被 cron 唤起，DONE 仅表示当前年度周期完成）
   - 放弃维持 → 归档终止，不再进入状态机

## 完成后

案件进入 `DONE` 终态（design.md 5.1 流转图）。年费监控在案件专利有效期内持续存在，由 `hooks/monthly_annuity_scan.yaml` 逐年唤起。
