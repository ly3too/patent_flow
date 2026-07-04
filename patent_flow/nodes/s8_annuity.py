"""S8 授权年费 — fully automatic: grant/annuity due-date monitoring, PM decision card,
payment instruction email draft.

human_gate: pm_maintain_decision (P1 priority, see skills/task/patent-grant-annuity/SKILL.md)
triggers: annuity_due
on_complete: DONE
"""


def run(case: dict) -> dict:
    raise NotImplementedError("S8 annuity handler not yet implemented")
