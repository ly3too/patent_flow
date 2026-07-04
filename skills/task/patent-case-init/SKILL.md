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

## 存储位置（唯一根空间，全部在企业知识库里）

所有案件资源统一挂在公司知识库的 `patent_flow` Wiki 空间下（**空间本身就是根**，token 记为 `$PATENT_FLOW_ROOT_TOKEN` = 该空间的 `space_id`，一次性获取，见 design.md 9.1），**不要在租户顶层另建平行目录，也绝对不要落到任何人的个人云空间（我的空间）**——这是调试时踩过的真实坑：`drive +create-folder` 不传 `--folder-token` 时默认建在调用者的个人空间下，必须显式给 wiki 节点或其他空间内 token 作为目标。

Wiki 节点没有 `folder` obj_type（只有 `doc/sheet/bitable/mindnote/docx/file/slides`），"目录"用**纯粹当父节点用的 docx 节点**模拟：

```
$PATENT_FLOW_ROOT_TOKEN（patent_flow 这个 Wiki 空间本身）
├── 专利总台账.bitable
├── templates（docx 节点，仅当父节点占位）
│    └── 案件主文档模板.docx（子节点）
└── cases（docx 节点，仅当父节点占位）
     └── <年份>（docx 节点，仅当父节点占位）
          └── <案号> - <案件名>     ← 本 skill 创建的就是这个节点本身，即案件主文档，不是"文件夹里的一个文件"
```

## 执行步骤

> 以下命令名已对照实际安装的 lark-cli（1.0.53）核实，与 design.md 9.2 节的伪代码不完全一致——那里的 `+folder-create`/`docs +copy`/`base +record-create`/`--announcement` 在真实 CLI 里都不存在或参数不同，下面是验证过的真实用法。

1. 生成案号（`YYYY + 流水号 + 品线代码`，如 `2026017CNU`）
2. 确认/创建当年的父节点：若 `cases/<年份>` 节点已存在直接复用其 token；不存在则 `lark-cli wiki +node-create --parent-node-token "<cases节点token>" --obj-type docx --title "<年份>"`（`cases` 节点本身若不存在，先用 `--space-id "$PATENT_FLOW_ROOT_TOKEN"` 建一次，不要重复建）
3. 建案件节点/主文档：
   - 有模板时：`lark-cli drive files copy --params '{"file_token":"<模板token>"}' --data '{"name":"<案号> - <案件名>","type":"docx","folder_token":"<临时Drive文件夹或直接父节点token>"}'` 复制出一份普通 Drive 文档，再 `lark-cli wiki +move --obj-type docx --obj-token <复制出的doc token> --target-space-id "$PATENT_FLOW_ROOT_TOKEN" --target-parent-token "<年份节点token>"` 迁入 wiki（`docs` 域没有 `+copy` shortcut，复制必须用 `drive files copy` 原生命令）
   - 没有模板时：直接 `lark-cli wiki +node-create --parent-node-token "<年份节点token>" --obj-type docx --title "<案号> - <案件名>"` 建一个空节点，再用 `docs +update --api-version v2 --command overwrite` 按 design.md 4.3 结构写入内容
   - 需要挂二进制附件（PDF 等）时用 `lark-cli drive +upload --wiki-token <案件节点token> --file <本地文件>`，不要另建文件夹
4. `lark-cli im +chat-create --as user --name "[<案号>] <案件名> - S1挖掘" --bots "<bot_app_id>"` 建一案一群（`--as user` 才能一步邀请其他人类成员并让 bot 自动入群；仅用 `--as bot` 建群时，邀请其他人类成员需要"先建群带上当前用户、再用 user 身份补邀其他人"的两步流程）
5. **群公告受限**：`im +chat-update` 只能改名字/描述，不支持 `--announcement`；原生 `PATCH /open-apis/im/v1/chats/:chat_id/announcement` 需要 `im:chat.announcement:read`/`write` scope——如果这两个 scope 还没在飞书开放平台后台给应用勾选，`auth login` 无论怎么重新授权都会报 `invalid or malformed scopes`（这是应用级权限缺失，不是用户没登录）。**当前替代方案**：发一条 `+messages-send --markdown` 状态消息，再用 `im pins create --data '{"message_id":"<刚发的消息id>"}'` 置顶，效果等价于设计里的"群公告"（design.md 6.2 本来也把 Pin 消息列为独立的群要素）。应用加上 announcement scope 后再切回真正的群公告。
6. 通过 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `append_event.sh`（内部是 `base +record-upsert`）写入首条事件
7. 写入台账主表（`$PATENT_FLOW_ROOT_TOKEN/专利总台账.bitable`）：`lark-cli base +record-upsert --base-token <base_token> --table-id <案件主表id> --json '{"案号":...,"群ID":...,...}'`（没有 `+record-create`，不传 `--record-id` 的 `+record-upsert` 就是创建）。因为案件没有真正的"文件夹"，`案件文件夹` 和 `案件主文档` 两个字段目前都填同一个案件节点的 wiki URL。

## 完成后

移交给 [patent-mining](../patent-mining/SKILL.md)（S1 挖掘），由顶层 [patent-flow](../../workflow/patent-flow/SKILL.md) 工作流负责调度。

## 硬规则

- 外部代理所不入群，仅走飞书邮件。
- 群默认"仅管理员可拉人"。
- 案号一旦生成即为主键，不可修改。
