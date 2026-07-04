---
name: patent-deadline-scan
version: "0.1.0"
layer: task
description: "跨案件期限监控任务：作为 OpenClaw 每日 cron 触发器，扫描 S6 优先权监听和 S8 授权年费这两个 cron 驱动节点上的全部案件，命中各自 REMIND_DAYS 提醒档位的当天生成催办。当日常定时 hook 触发，或需要人工手动巡检 S6/S8 待办时使用。不做具体节点业务处理（判定逻辑在 patent_flow/nodes/s6_priority.py 和 s8_annuity.py 里），也不覆盖 S1-S5/S7 等需要人工节奏推进的节点（那些节点没有固定周期，靠飞书事件/@bot 触发，见 [patent-flow](../../workflow/patent-flow/SKILL.md) 的路由表）。"
metadata:
  triggers: [cron_daily]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-deadline-scan（task 层：S6/S8 期限扫描）

对应 design.md 第 7.2 节「长流程不丢事」的兜底触发器：OpenClaw Hook cron。实现见 `patent_flow.workflow.scan_deadlines()`。

## 执行步骤

1. `tools/scan_deadlines.sh` → `patent_flow.workflow.scan_deadlines(today)`：对 `S6_priority_watch` 和 `S8_annuity` 两个节点分别 `list_cases_by_node()`，逐个 `dispatch()` 给对应 handler（不带 `pm_decision`，即只做"检查今天是否该提醒"）
2. 每个 handler（[patent-priority-watch](../patent-priority-watch/SKILL.md) 的 `REMIND_DAYS=[60,30,14]`，[patent-grant-annuity](../patent-grant-annuity/SKILL.md) 的 `REMIND_DAYS=[90,30,7]`）用**精确天数匹配**判断今天是否命中某个提醒档位，命中才返回 `needs_human=True`
3. 对命中的案件：通过 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `append_event.sh` 记录一次「催办」事件，群内 @等待对象 发送提醒卡片；档位到达 `ESCALATE_AT`（S6=14 天，S8=7 天）时同时 @leader
4. 未命中的案件（`needs_human=False`）不做任何动作，也不打扰任何人

## 关联 hooks

- `hooks/daily_deadline_scan.yaml`（每日 9:00，唯一的 cron 入口——是否真的提醒由第 2 步的天数匹配决定，不需要为 S6/S8 分别配置月度 cron）
