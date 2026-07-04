---
name: patent-filing
version: "0.1.0"
layer: task
description: "专利 S4 委案节点任务：全自动，无需人工 Approval Gate（仅走审批流）。案号生成校验、台账写入、委案邮件草稿生成并通过飞书邮件发给外部代理所。当案件当前节点为 S3_disclosure 交底审核通过后自动触发时使用。落地优先级 P1，建议最先实现。不负责回稿校验（[patent-review](../patent-review/SKILL.md)）。"
metadata:
  node: S4_filing
  handler: patent_flow/nodes/s4_filing.py
  auto: true
  triggers: [approval_passed]
  on_complete: [S5_review]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-filing（task 层：S4 委案，P1 全自动）

design.md 第十一节标注为 **P1 全自动**节点，建议最先落地——最直接减轻人力。

## 执行步骤（无需等待人工确认，approval_passed 触发即执行）

1. 校验案号唯一性，写入台账主表
2. 归档委案材料到案件文件夹
3. 生成委案邮件草稿（收件人：外部代理所，走飞书邮件，代理所不入群）
4. `tools/run_node.sh <案号> '{}'` — `patent_flow/nodes/s4_filing.py` 不需要任何输入：校验案号格式、生成邮件草稿文本（`result.extra["filing_email_draft"]`）并直接跳转 `S5_review`，这是唯一一个"空 inputs 也能跑完"的节点

## 完成后

移交 [patent-review](../patent-review/SKILL.md)（S5 回稿）。
