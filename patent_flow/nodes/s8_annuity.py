"""S8 授权年费 — fully automatic: grant/annuity due-date monitoring, PM decision card,
payment instruction email draft.

human_gate: pm_maintain_decision (P1 priority, see skills/task/patent-grant-annuity/SKILL.md)
triggers: annuity_due
on_complete: DONE
"""
from datetime import date

from .base import NodeResult, pick_reminder_tier
from ..dates import parse_date

REMIND_DAYS = [90, 30, 7]
ESCALATE_AT = 7
VALID_DECISIONS = {"继续缴费", "放弃维持"}


def draft_payment_email(case: dict) -> str:
    return f"缴费指令\n\n案号：{case['案号']}\n请代理所协助办理本年度年费缴纳手续。"


def run(case: dict, today: date, pm_decision: str | None = None) -> NodeResult:
    if pm_decision is not None:
        if pm_decision not in VALID_DECISIONS:
            raise ValueError(f"未知维持决策 {pm_decision!r}，应为 {VALID_DECISIONS}")
        if pm_decision == "继续缴费":
            return NodeResult(
                to_node="DONE",
                evidence="PM 决定继续维持，已生成缴费指令邮件草稿",
                summary="年费已缴，案件本年度周期完成",
                events=[("annuity_decision", "继续缴费")],
                extra={"payment_email_draft": draft_payment_email(case)},
            )
        return NodeResult(
            to_node="DONE",
            evidence="PM 决定放弃维持",
            summary="放弃缴纳年费，专利终止维持",
            events=[("annuity_decision", "放弃维持")],
        )

    deadline = parse_date(case["年费到期日"])
    days_left = (deadline - today).days
    tier = pick_reminder_tier(days_left, REMIND_DAYS)

    if tier is None:
        return NodeResult(
            to_node=None,
            evidence="",
            summary=f"年费到期还剩 {days_left} 天，未到提醒节点",
        )

    escalate = tier <= ESCALATE_AT
    summary = f"⏰ 年费维持决策提醒：距到期还剩 {days_left} 天"
    if escalate:
        summary += "（已升级 @leader）"
    return NodeResult(
        to_node=None,
        evidence="",
        summary=summary,
        events=[("annuity_reminder", f"{tier} 天档催办" + ("，已升级" if escalate else ""))],
        needs_human=True,
        human_gate="pm_maintain_decision",
    )
