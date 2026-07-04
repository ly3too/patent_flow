"""S6 优先权监听 — fully automatic: monthly ledger scan, PM decision card generation.

human_gate: pm_priority_decision (P1 priority, see skills/task/patent-priority-watch/SKILL.md)
triggers: cron_monthly, ten_month_due
parallel_to: S7_oa
on_complete: S7_oa
"""
from datetime import date

from .base import NodeResult, pick_reminder_tier
from ..dates import add_months, parse_date

REMIND_DAYS = [60, 30, 14]
ESCALATE_AT = 14
VALID_DECISIONS = {"申请美国", "申请欧洲", "都申请", "放弃"}


def priority_deadline(case: dict) -> date:
    return add_months(parse_date(case["申请日"]), 10)


def run(case: dict, today: date, pm_decision: str | None = None) -> NodeResult:
    if pm_decision is not None:
        if pm_decision not in VALID_DECISIONS:
            raise ValueError(f"未知优先权决策 {pm_decision!r}，应为 {VALID_DECISIONS}")
        return NodeResult(
            to_node="S7_oa",
            evidence=f"PM 优先权决策：{pm_decision}",
            summary=f"优先权决策已回填：{pm_decision}",
            events=[("pm_priority_decision", pm_decision)],
        )

    deadline = priority_deadline(case)
    days_left = (deadline - today).days
    tier = pick_reminder_tier(days_left, REMIND_DAYS)

    if tier is None:
        return NodeResult(
            to_node=None,
            evidence="",
            summary=f"优先权到期还剩 {days_left} 天，未到提醒节点",
        )

    escalate = tier <= ESCALATE_AT
    summary = f"⏰ 优先权决策提醒：距到期还剩 {days_left} 天"
    if escalate:
        summary += "（已升级 @leader）"
    return NodeResult(
        to_node=None,
        evidence="",
        summary=summary,
        events=[("priority_reminder", f"{tier} 天档催办" + ("，已升级" if escalate else ""))],
        needs_human=True,
        human_gate="pm_priority_decision",
    )
