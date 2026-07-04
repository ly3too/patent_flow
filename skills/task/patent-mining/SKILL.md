---
name: patent-mining
version: "0.1.0"
layer: task
description: "专利 S1 挖掘节点任务：读取挖掘会议纪要和研发上传的技术资料，提炼技术问题/技术方案/技术效果三要素草稿，交 IPR 确认后流转到 S2 查新。当案件当前节点为 S1_mining，或群内出现研发上传技术说明/3D模型/会议纪要时使用。不负责查新检索（[patent-search](../patent-search/SKILL.md)）或状态写入（走 [patent-cli](../../tool/patent-cli/SKILL.md)）。"
metadata:
  node: S1_mining
  handler: patent_flow/nodes/s1_mining.py
  human_gate: ipr_confirm_three_elements
  on_complete: [S2_search]
  priority: P2
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-mining（task 层：S1 挖掘）

## 触发场景

```
Bot: @研发 请上传技术说明和 3D 模型图
研发: [上传 2 个文件]
Bot: 已归档到 📁 01_挖掘/, AI 提炼出 3 个待澄清问题 ...
     [开始挖掘会] [先改提纲]
```

## 执行步骤

1. 用 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `load_case.sh` 读取案件当前状态
2. 归档群内上传文件到云盘 `01_挖掘/`（走 lark-cli drive）
3. 从会议纪要/技术说明中提炼「技术问题 / 技术方案 / 技术效果」草稿，写入主文档 `agent:elements` 区块
4. 生成待澄清问题列表，@研发 或 @IPR 确认
5. IPR 确认三要素完整后（`human_gate: ipr_confirm_three_elements`），调用 `transition.sh <案号> S2_search <依据>`

## 超期处理

`timeout: 7d`，超期未确认则升级提醒 IPR。

## 完成后

移交 [patent-search](../patent-search/SKILL.md)（S2 查新）。
