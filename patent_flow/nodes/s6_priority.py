"""S6 优先权监听 — fully automatic: monthly ledger scan, PM decision card generation.

human_gate: pm_priority_decision (P1 priority, see skills/task/patent-priority-watch/SKILL.md)
triggers: cron_monthly, ten_month_due
parallel_to: S7_oa
"""

REMIND_DAYS = [60, 30, 14]


def run(case: dict) -> dict:
    raise NotImplementedError("S6 priority watch handler not yet implemented")
