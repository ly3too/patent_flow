---
name: patent-disclosure
version: "0.1.0"
layer: task
description: "专利 S3 交底节点任务：下发技术交底书模板，做格式校验和图号一致性检查，IPR 审核通过后流转到 S4 委案。当案件当前节点为 S3_disclosure 时使用。不负责查新判定（[patent-search](../patent-search/SKILL.md)）或委案全自动流程（[patent-filing](../patent-filing/SKILL.md)）。"
metadata:
  node: S3_disclosure
  handler: patent_flow/nodes/s3_disclosure.py
  human_gate: ipr_review_disclosure
  on_complete: [S4_filing]
  priority: P3
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-disclosure（task 层：S3 交底）

## 执行步骤

1. 下发 `技术交底书` 模板到案件文件夹
2. 研发填写后，校验格式完整性（章节齐全）与图号一致性（正文引用的图号与附图是否对应）
3. 归档为 `03_技术交底书_vN.docx`
4. IPR 审核通过（`human_gate: ipr_review_disclosure`）→ `transition.sh <案号> S4_filing <依据>`

## 超期处理

`timeout: 14d`。

## 完成后

移交 [patent-filing](../patent-filing/SKILL.md)（S4 委案，全自动）。
