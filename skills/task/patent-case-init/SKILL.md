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
├── 专利流程管理.bitable
├── templates（docx 节点，仅当父节点占位）
│    └── 案件主文档模板.docx（子节点）
└── cases（docx 节点，仅当父节点占位）
     └── <年份>（docx 节点，仅当父节点占位）
          └── <案号> - <案件名>     ← 本 skill 创建的就是这个节点本身，即案件主文档，不是"文件夹里的一个文件"
```

## 执行步骤

> 以下命令名已对照实际安装的 lark-cli（1.0.53）核实，与 design.md 9.2 节的伪代码不完全一致——那里的 `+folder-create`/`docs +copy`/`base +record-create`/`--announcement` 在真实 CLI 里都不存在或参数不同，下面是验证过的真实用法。

1. 生成案号：`tools/new_case_no.sh`（即 `python -m patent_flow new-case-no`）——规则是 `YYYYMMDD + 5位随机大写字母`（如 `20260705ABCDE`），命令内部会查台账主表，撞号自动重试，不需要也不要自己在对话里手算或瞎编一个案号
2. 确认/创建当年的父节点：若 `cases/<年份>` 节点已存在直接复用其 token；不存在则 `lark-cli wiki +node-create --parent-node-token "<cases节点token>" --obj-type docx --title "<年份>"`（`cases` 节点本身若不存在，先用 `--space-id "$PATENT_FLOW_ROOT_TOKEN"` 建一次，不要重复建）
3. 建案件节点/主文档：
   - 有模板时：`lark-cli drive files copy --params '{"file_token":"<模板token>"}' --data '{"name":"<案号> - <案件名>","type":"docx","folder_token":"<临时Drive文件夹或直接父节点token>"}'` 复制出一份普通 Drive 文档，再 `lark-cli wiki +move --obj-type docx --obj-token <复制出的doc token> --target-space-id "$PATENT_FLOW_ROOT_TOKEN" --target-parent-token "<年份节点token>"` 迁入 wiki（`docs` 域没有 `+copy` shortcut，复制必须用 `drive files copy` 原生命令）
   - 没有模板时：直接 `lark-cli wiki +node-create --parent-node-token "<年份节点token>" --obj-type docx --title "<案号> - <案件名>"` 建一个空节点，再用 `docs +update --api-version v2 --command overwrite` 按 design.md 4.3 结构写入内容
   - 需要挂二进制附件（PDF 等）时用 `lark-cli drive +upload --wiki-token <案件节点token> --file <本地文件>`，不要另建文件夹
4. `lark-cli im +chat-create --as user --name "[<案号>] <案件名> - S1挖掘" --bots "$LARK_CLI_APP_ID,$OPENCLAW_APP_ID"` 建一案一群（`--as user` 才能一步邀请其他人类成员并让 bot 自动入群；仅用 `--as bot` 建群时，邀请其他人类成员需要"先建群带上当前用户、再用 user 身份补邀其他人"的两步流程）。**两个 bot 都要拉**：`$LARK_CLI_APP_ID` 是 lark-cli 当前绑定/创建的应用（`lark-cli config show` 查得到），`$OPENCLAW_APP_ID` 是 OpenClaw 自己配置的飞书应用（读 `~/.openclaw/openclaw.json` 的 `channels.feishu.appId`）——这两个**很可能不是同一个应用**（我们自己的调试环境就是两个不同的 app id），只拉 lark-cli 的那个会导致 OpenClaw 收不到群里的消息事件。`scripts/install.sh` 已经把这两个值解析进 `.env.patent_flow`；如果某个变量是空的说明对应的应用没配（比如没装 OpenClaw），只拉有值的那个即可。已建好的群事后要补拉，用 `lark-cli im chat.members create --params '{"chat_id":"<chat_id>","member_id_type":"app_id"}' --data '{"id_list":["<app_id>"]}'`。
5. **设置群公告 + 置顶**（都用 bot 身份，见下方"消息发送身份"）：
   - 群公告走 `patent_flow.store.LarkIM.set_announcement(chat_id, text)`（`tools/run_node.sh`/`transition.sh` 内部会自动调用，不需要手拼）。真实实现是"升级版群公告"的 docx block API，不是 `im +chat-update --announcement`（那个 flag 根本不存在）：
     - 读现有内容：`GET /open-apis/docx/v1/chats/:chat_id/announcement/blocks/:chat_id/children`（**根 block_id 就是 chat_id 本身**）
     - 清空：`DELETE .../children/batch_delete --data '{"start_index":0,"end_index":<现有块数>}'`（先读数量，非空才删，避免每次都无意义调用）
     - 写入：`POST .../children --data '{"children":[{"block_type":2,"text":{"elements":[{"text_run":{"content":"<正文>"}}]}}]}'`（block_type=2 是文本块）
     - 需要 `im:chat.announcement:read` + `im:chat.announcement:write_only`（**不是 `:write`**，这个坑踩过一次）在飞书开发者后台给应用勾选；`auth login` 重新走一遍才能拿到（`scripts/install.sh` 已经在 `ensure_user_auth` 里顺带申请了这两个 scope，如果后台还没勾选会申请失败但不阻塞安装）。
     - **降级方案**：如果 `set_announcement` 因为 scope 缺失而报错（`subprocess.CalledProcessError`），`patent_flow.transition._set_announcement_with_fallback()` 会自动改为发一条状态消息再 `im pins create` 置顶——群公告和 Pin 消息本来就是 design.md 6.2 里两个独立的群要素，降级不算偷工减料。
   - Pin 消息（design.md 6.2 的独立要素，无论群公告是否可用都发）：发一条状态消息，`im pins create --data '{"message_id":"<刚发的消息id>"}'`。
6. 通过 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `append_event.sh`（内部是 `base +record-upsert`）写入首条事件
7. 写入台账主表（`$PATENT_FLOW_ROOT_TOKEN/专利流程管理.bitable`）：`lark-cli base +record-upsert --base-token <base_token> --table-id <案件主表id> --json '{"案号":...,"群ID":...,"IPR":[{"id":"<IPR的open_id>"}],"研发":[{"id":"<研发1的open_id>"},{"id":"<研发2的open_id>"}],...}'`（没有 `+record-create`，不传 `--record-id` 的 `+record-upsert` 就是创建）。因为案件没有真正的"文件夹"，`案件文件夹` 和 `案件主文档` 两个字段目前都填同一个案件节点的 wiki URL。`IPR`/`研发` 是人员字段，值是 `{"id": open_id}` 对象数组（`研发` 允许多个），不知道 open_id 时先 `lark-cli contact +search-user --query "<姓名>" --as user` 查一遍，不要瞎猜。

## 完成后

移交给 [patent-mining](../patent-mining/SKILL.md)（S1 挖掘），由顶层 [patent-flow](../../workflow/patent-flow/SKILL.md) 工作流负责调度。

## 硬规则

- 外部代理所不入群，仅走飞书邮件。
- 群默认"仅管理员可拉人"。
- 案号一旦生成即为主键，不可修改。
- **案件节点标题永远是「案号 - 案件名」**（如 `2026017CNU - 电视挂架自适应卡扣`），不要用固定的 `00_案件主文档` 这种通用名字——多个案件都叫这个名字会没法区分。design.md 9.2 节的伪代码历史上示例过 `00_案件主文档`，那是旧写法，不要照抄。
- **消息发送身份**：建群（`+chat-create`，需要一步邀请人类成员）用 `--as user`；建群之后的一切群内操作——改名、发消息、置顶、设群公告——都用 `--as bot`（`patent_flow.store.LarkIM` 已经这样实现），Agent 是以「机器人」身份在群里活动，不是冒充 IPR 本人说话。
