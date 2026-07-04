---
name: patent-case-init
version: "0.1.0"
layer: task
description: "专利新案件初始化任务：一案一群创建。建案件云盘文件夹、从模板复制主文档、创建飞书群并邀请 IPR/研发/PM、写入台账主表、设置群公告与群名。当 IPR 说'新建案件'或群 ID/案号在台账中还不存在时使用。不负责后续 8 节点的具体业务处理（那些是各自的 task skill），也不负责底层 lark-cli 参数拼装（那是 [patent-cli](../../tool/patent-cli/SKILL.md)）。"
metadata:
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
    env:
      - PATENT_FLOW_ROOT_TOKEN
  human_gate: none
  priority: P1
---

# patent-case-init（task 层：一案一群初始化）

对应 design.md 第 9.2 节的初始化脚本，是所有案件生命周期的入口。

## 触发场景

```
IPR @bot: 新建案件 电视挂架自适应卡扣 品线=家庭影音 研发=@李四@王五
Bot: 已创建群「[2026017CNU] 电视挂架自适应卡扣」, 已邀请成员
```

## 存储位置（唯一根目录）

所有案件资源统一挂在公司知识库的 `patent_flow/` 根节点下（token 记为 `$PATENT_FLOW_ROOT_TOKEN`，一次性获取，见 design.md 9.1），不要在租户顶层另建平行目录：

```
$PATENT_FLOW_ROOT_TOKEN (patent_flow/)
├── 专利总台账.bitable
├── templates/案件主文档模板.docx
└── cases/<年份>/<案号> - <案件名>/     ← 本 skill 创建的案件文件夹
```

## 执行步骤

1. 生成案号（`YYYY + 流水号 + 品线代码`，如 `2026017CNU`）
2. `lark-cli drive +folder-create --parent-token "$PATENT_FLOW_ROOT_TOKEN/cases/<年份>"` 建案件文件夹
3. `lark-cli docs +copy` 从 `$PATENT_FLOW_ROOT_TOKEN/templates/案件主文档模板.docx` 复制主文档到案件文件夹
4. `lark-cli im +chat-create` 建一案一群，邀请 IPR（管理员）+ 研发 + PM
5. `lark-cli im +chat-update` 设置群公告（当前节点 S1.1 + 指向 `cases/<年份>/<案号>.../00_案件主文档.docx` 的链接）
6. 通过 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `append_event.sh` 写入首条事件
7. `lark-cli base +record-create` 写入台账主表（`$PATENT_FLOW_ROOT_TOKEN/专利总台账.bitable`）：案号 / 群ID / 案件文件夹 / 案件主文档 / 当前节点=S1 / 状态=running

## 完成后

移交给 [patent-mining](../patent-mining/SKILL.md)（S1 挖掘），由顶层 [patent-flow](../../workflow/patent-flow/SKILL.md) 工作流负责调度。

## 硬规则

- 外部代理所不入群，仅走飞书邮件。
- 群默认"仅管理员可拉人"。
- 案号一旦生成即为主键，不可修改。
