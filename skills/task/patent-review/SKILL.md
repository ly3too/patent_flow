---
name: patent-review
version: "0.1.0"
layer: task
description: "专利 S5 回稿节点任务：对代理所回稿的正式申请文件做形审 diff、错别字检查、权利要求引用关系校验，IPR 范围审查通过后流转到 S6 优先权监听（默认并行）或直接进入 S7 OA（如已收到审查意见）。当案件当前节点为 S5_review 时使用。不负责委案（[patent-filing](../patent-filing/SKILL.md)）或优先权监听（[patent-priority-watch](../patent-priority-watch/SKILL.md)）。"
metadata:
  node: S5_review
  handler: patent_flow/nodes/s5_review.py
  human_gate: ipr_scope_review
  on_complete: [S6_priority_watch, S7_oa]
  priority: P3
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-review（task 层：S5 回稿）

## 执行步骤

1. 对比代理所回稿与委案材料，生成形审 diff（新增/删除/修改的技术特征）
2. 错别字检查、权利要求引用关系校验（引用的权利要求号是否存在、是否成环）
3. 归档为 `05_代理稿_vN.docx`
4. IPR 范围审查通过（`human_gate: ipr_scope_review`）后二选一：
   - 默认：`transition.sh <案号> S6_priority_watch <依据>`（进入优先权监听，与 S7 并行等待）
   - 若已直接收到审查意见：`transition.sh <案号> S7_oa <依据>`

## 超期处理

`timeout: 30d`。

## 完成后

移交 [patent-priority-watch](../patent-priority-watch/SKILL.md)（S6，全自动）和/或 [patent-oa](../patent-oa/SKILL.md)（S7）。
