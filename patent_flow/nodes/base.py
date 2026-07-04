"""Shared types for node handlers.

Every `patent_flow/nodes/*.py` module exposes `run(case: dict, **inputs) ->
NodeResult`. Handlers are pure decision functions: they never call `lark-cli`
or `transition()` themselves. `workflow.dispatch()` validates the proposed
`to_node` against the state machine, and `workflow.apply_result()` is the
only thing that actually calls `transition()`.
"""
from dataclasses import dataclass, field


@dataclass
class NodeResult:
    """`to_node=None` means "stay put" — still waiting on a human_gate or a
    deadline that hasn't arrived yet. The workflow only calls `transition()`
    when `to_node` is set."""

    to_node: str | None
    evidence: str
    summary: str
    events: list[tuple[str, str]] = field(default_factory=list)
    needs_human: bool = False
    human_gate: str | None = None
    extra: dict = field(default_factory=dict)


def pick_reminder_tier(days_left: int, tiers: list[int]) -> int | None:
    """Daily-cron reminder check: fire only on the exact day a tier is hit.

    `tiers` is a list of "days before deadline" thresholds, e.g. [60, 30, 14].
    Returns the matching tier, or None if today isn't one of them.
    """
    return days_left if days_left in tiers else None
