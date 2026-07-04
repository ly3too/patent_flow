---
name: patent-search
version: "0.1.0"
layer: task
description: "专利 S2 查新节点任务：基于三要素生成检索式，调用外部检索工具（如智慧芽）获取对比文件，产出特征拆解对比表，供 IPR 判定是否有新创性并决定流转到 S3 交底或终止案件。当案件当前节点为 S2_search 时使用。不负责挖掘阶段的三要素提炼（[patent-mining](../patent-mining/SKILL.md)）或状态写入（[patent-cli](../../tool/patent-cli/SKILL.md)）。"
metadata:
  node: S2_search
  handler: patent_flow/nodes/s2_search.py
  human_gate: ipr_decide_continue
  on_complete: [S3_disclosure, TERMINATED]
  priority: P2
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-search（task 层：S2 查新）

## 执行步骤

1. `load_case.sh` 读取主文档 `agent:elements` 区块（技术三要素）
2. 生成检索式，调用外部检索工具（Playwright + 本地 keychain 账号密码，无官方 API）
3. 产出特征拆解对比表，归档到 `02_查新报告.docx`
4. @IPR 判定：方案与对比文件的差异性是否足够构成新创性

## 关键分支（唯一有 TERMINATED 出口的节点）

```
tools/run_node.sh <案号> '{"ipr_verdict": "无新创性", "evidence": "..."}'   # → TERMINATED
tools/run_node.sh <案号> '{"ipr_verdict": "有新创性", "evidence": "..."}'   # → S3_disclosure
```

`patent_flow/nodes/s2_search.py` 的 `run()` 对 `ipr_verdict` 做枚举校验（只接受"有新创性"/"无新创性"），传其它值直接抛错，不会静默误判。

## 超期处理

`timeout: 14d`。

## 完成后

移交 [patent-disclosure](../patent-disclosure/SKILL.md)（S3 交底），或案件终止归档。
