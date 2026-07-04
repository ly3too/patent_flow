---
name: patent-oa
version: "0.1.0"
layer: task
description: "专利 S7 OA审查节点任务：收到审查意见通知书后，拉取对比文件、生成反驳论点草稿，IPR 定稿后流转到 S8 授权年费。当案件当前节点为 S7_oa，或群内出现 OA 通知书 PDF 上传时使用。不负责优先权决策（[patent-priority-watch](../patent-priority-watch/SKILL.md)）或授权年费监控（[patent-grant-annuity](../patent-grant-annuity/SKILL.md)）。"
metadata:
  node: S7_oa
  handler: patent_flow/nodes/s7_oa.py
  human_gate: ipr_finalize_response
  on_complete: [S8_annuity]
  priority: P2
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-oa（task 层：S7 OA审查）

## 执行步骤

1. 归档 OA 通知书到 `07_OA通知书.pdf`
2. 拉取审查意见引用的对比文件
3. 生成反驳论点草稿（技术特征差异比对）
4. IPR 定稿（`human_gate: ipr_finalize_response`）→ `transition.sh <案号> S8_annuity <依据>`

## 超期处理

`timeout: 90d`（OA 答复期限通常较长，需结合官方给定的答复截止日）。

## 完成后

移交 [patent-grant-annuity](../patent-grant-annuity/SKILL.md)（S8，全自动）。
