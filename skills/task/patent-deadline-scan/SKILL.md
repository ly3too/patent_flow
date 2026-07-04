---
name: patent-deadline-scan
version: "0.1.0"
layer: task
description: "跨节点期限监控任务：作为 OpenClaw cron 兜底触发器（每日9:00扫描），对台账中'截止日期 < TODAY()+3'的全部案件（不限具体节点）做统一告警催办，防止任何飞书回调遗漏导致的超期。当日常定时 hook 触发，或需要人工手动巡检全量待办时使用。不做具体节点业务处理，命中的案件仍交给对应节点的 task skill（如 [patent-priority-watch](../patent-priority-watch/SKILL.md)、[patent-grant-annuity](../patent-grant-annuity/SKILL.md)）处理。"
metadata:
  triggers: [cron_daily, bitable_automation_webhook]
  priority: P1
  requires:
    skills: ["../../tool/patent-cli/SKILL.md"]
---

# patent-deadline-scan（task 层：期限兜底扫描）

对应 design.md 第 7.2 节「长流程不丢事」的三套唤醒触发器中的后两套：OpenClaw Hook cron + 多维表格自动化。

## 执行步骤

1. `tools/scan_deadlines.sh <天数>`（默认 3 天）读取「待办/截止」视图：`状态=waiting_human AND 截止日期 < TODAY()+3`
2. 对每条命中记录，按其「当前节点」路由到对应 task skill 继续处理（S6→[patent-priority-watch](../patent-priority-watch/SKILL.md)，S8→[patent-grant-annuity](../patent-grant-annuity/SKILL.md)，其余节点按 `当前节点` 字段路由）
3. 通过 [patent-cli](../../tool/patent-cli/SKILL.md) 的 `append_event.sh` 记录一次「催办」事件
4. 群内 @等待对象 发送催办卡片；连续 N 次未响应则升级 @leader

## 关联 hooks

- `hooks/daily_oa_deadline.yaml`（每日 9:00）
- `hooks/monthly_priority_scan.yaml`（每月 1 日）
- `hooks/monthly_annuity_scan.yaml`（每月 1 日）
