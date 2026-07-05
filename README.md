# patent-flow-skill

专利全生命周期管理的 AI Agent Skill 包 —— 由 Claude Code / OpenClaw 驱动，飞书（知识库 + 多维表格 + 一案一群）做唯一存储。完整设计见 [design.md](design.md)，代码架构见 [CLAUDE.md](CLAUDE.md)。

## 前置条件

- 一个飞书（Feishu）租户，你在里面能建应用 / 建知识库 / 建群
- 已安装 [Claude Code](https://claude.com/claude-code) 和/或 [OpenClaw](https://openclaw.dev)（至少一个）
- [Node.js](https://nodejs.org)（`npm install -g lark-cli` 需要）
- 一个 Python **>= 3.10** 的解释器（系统自带的 `python3` 在 macOS 上通常是 3.9，太旧；用 `brew install python@3.12` 之类装一个新的即可，装完不需要手动配置——安装脚本会自己找到它）

## 一键安装

```bash
git clone <本仓库地址>
cd patent_flow
bash scripts/install.sh
```

脚本是幂等的，重复运行安全（每一步都会先检查资源是否已存在，不会重复创建）。它会依次：

1. **安装 lark-cli**（`npm install -g @larksuiteoapi/lark-cli`，已安装则跳过）
2. **绑定 / 创建飞书应用**：
   - 如果你在 OpenClaw 环境里运行（检测到 `$OPENCLAW_HOME`），会问你要不要把 lark-cli 绑定到 OpenClaw 已有的飞书应用上（需要确认使用 user 身份，因为本项目要读写你自己的云空间/知识库/群聊）
   - 否则会跑 `lark-cli config init --new`，打开浏览器引导你创建一个新应用
   - 已经配置过的话直接跳过
3. **用户身份授权**（`lark-cli auth login`，浏览器扫码/点链接）
4. **初始化飞书知识库**：新建（或复用已有的）`patent_flow` 知识库空间、`专利流程管理.bitable`（含 `案件主表`/`事件流水` 两张表和全部字段）、`templates`/`cases` 占位节点
5. **识别机器人应用 ID**：`lark-cli` 绑定的应用（`LARK_CLI_APP_ID`）和 OpenClaw 自己配置的应用（`OPENCLAW_APP_ID`，从 `~/.openclaw/openclaw.json` 读）——**这两个很可能不是同一个应用**（我们自己的调试环境就是两个不同的 app id），建群时要把两个 bot 都拉进去，只拉一个会导致其中一端收不到群消息
6. **安装 Python 依赖**（自动找一个 >=3.10 的解释器，找不到会报错并提示你装一个）
7. **软链 skills**：把 `skills/` 下的 13 个技能链接进 `~/.claude/skills/` 和/或 `~/.openclaw/skills/`（只会链接你实际装了的那个/那些）
8. **跑一遍测试**，确认环境没问题

跑完会把所有资源 token 写到仓库根目录的 `.env.patent_flow` 里，`tools/*.sh` 和 `python -m patent_flow` 都会自动读取这个文件（不需要你手动 `export`）。

## 权限检查清单（重要）

`lark-cli auth login` 默认按 `--domain base,contact,docs,drive,im,wiki` 请求权限，覆盖了本项目日常用到的绝大部分能力。但如果你的飞书应用是全新创建的，某些权限可能还没在应用的权限列表里"申请"过——这种情况下 `auth login` 或具体的 API 调用会报 `permission_violations` / `invalid or malformed scopes`。

遇到这种报错，去飞书开放平台后台（开发者控制台）→ 你的应用 → 权限管理，搜索并开通对应权限。本项目用到的权限：

| 领域 | 权限（搜索关键字） | 用途 |
|---|---|---|
| 多维表格 | `base:app:*`、`base:table:*`、`base:field:*`、`base:record:*` | 专利总台账的建表/建字段/读写记录 |
| 知识库 | `wiki:space:*`、`wiki:node:*` | 建知识库空间、建/移动案件节点 |
| 云文档 | `docx:document:*`、`docs:document:copy` | 案件主文档的创建、编辑、从模板复制 |
| 云空间 | `drive:file:upload`、`drive:file:download`、`drive:drive.metadata:readonly`、`space:folder:create`、`space:document:move` | 附件上传/下载、临时文件操作 |
| 即时通讯 | `im:chat:create_by_user`、`im:chat:read`、`im:chat:update`、`im:chat.members:*`、`im:message`、`im:message:readonly`、`im:message.pins:*` | 一案一群的创建、改名、发消息、置顶状态 |
| 通讯录 | `contact:user.base:readonly`、`contact:user.basic_profile:readonly`、`contact:user:search` | 按姓名/邮箱查 `open_id`（如解析 IPR/研发人员） |
| 群公告（单独申请） | `im:chat.announcement:read`、`im:chat.announcement:write_only`（**注意是 `write_only` 不是 `write`**，写错名字 `auth login` 会直接报 `invalid or malformed scopes`） | 群公告的真实实现（`LarkIM.set_announcement()`），必须先在开发者后台手动给应用加上这两个权限，`auth login`/`install.sh` 才可能申请到——这两个权限不在 `--domain` 的任何预设组合里 |

`scripts/install.sh` 会在拿到 `--domain` 权限后，自动追加尝试申请这两个群公告权限；如果后台还没勾选，这一步会失败但不影响安装继续——`patent-case-init` 检测到群公告不可用时会自动降级为「Pin 消息」代替（design.md §6.2 本来也把 Pin 列为独立的群要素，不算功能缺失）。

## 验证安装

安装完成后，在 Claude Code 或 OpenClaw 里对 Agent 说类似：

```
新建一个专利案件：多功能车载充电器，品线=测试，IPR=我，研发=我
```

会触发 `patent-case-init` 这个 skill，实际在飞书里创建：一个案件文档节点（挂在 `patent_flow` 知识库的 `cases/<年份>/` 下）、一个一案一群的群聊、台账主表里的一条记录。

也可以不经过 Agent，直接跑一遍底层命令确认环境本身没问题：

```bash
source .env.patent_flow
tools/new_case_no.sh          # 应该打印一个形如 20260705ABCDE 的案号
$PYTHON -m patent_flow status # 列出每个节点当前有多少案件（应该都是 0，除非之前建过）
```

## 常见坑（真实调试过程中踩过的）

- **不要让资源落到个人云空间（我的空间）**：`lark-cli drive +create-folder` 不传 `--folder-token` 时默认建在调用者个人空间下。`scripts/setup_feishu_infra.sh` 已经避开了这个问题（一切都在 `patent_flow` 知识库空间内创建），但如果你自己手写脚本要小心。
- **Wiki 节点没有 `folder` 这个 obj_type**：只有 `doc/sheet/bitable/mindnote/docx/file/slides`。案件"目录"是用纯粹当父节点用的 docx 节点模拟的，不是真正的文件夹。
- **案件主文档标题永远是「案号 - 案件名」**，不要用固定的通用文件名——多个案件都叫一样的名字会没法区分。
- **系统 Python 太旧**：patent_flow 代码用了 3.10+ 语法（如 `str | None`），系统自带的 `python3`（macOS 上常是 3.9）会直接报 `TypeError`。用 `$PYTHON`（`install.sh` 已经帮你找好并写进 `.env.patent_flow`）而不是裸的 `python`/`python3`。
- **群公告不是 `im +chat-update --announcement`**：这个 flag 根本不存在。真实 API 是"升级版群公告"的 docx block 接口（`docx/v1/chats/:chat_id/announcement/blocks/:chat_id/children`），根 block_id 就是 chat_id 本身；`create children` 只会追加，"替换公告"要先读现有块数再 `batch_delete`。已经封装成 `patent_flow.store.LarkIM.set_announcement()`。
- **lark-cli 绑定的应用不等于 OpenClaw 的应用**：两者的 app_id 可能不同，建群时要把两个 bot 都拉进去（`scripts/install.sh` 已经把两个 app_id 解析进 `.env.patent_flow`）。
- **群内消息一律以 bot 身份发**：建群本身用 `--as user`（一步邀请人类成员），但改名/群公告/置顶/播报都用 `--as bot`——Agent 是以机器人身份活动，不是冒充登录的那个人。

## 更多文档

- [design.md](design.md) —— 完整方案设计（存储拓扑、状态机、一案一群范式、Lark CLI 用法）
- [CLAUDE.md](CLAUDE.md) —— 给 Claude Code 看的代码架构说明（模块职责、命令速查）
- `skills/workflow/patent-flow/SKILL.md` —— 顶层编排 skill，从这里开始读三层 Skill 体系
