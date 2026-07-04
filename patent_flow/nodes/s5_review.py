"""S5 回稿 — formality diff, typo check, reference-consistency check on agent draft.

human_gate: ipr_scope_review (see skills/task/patent-review/SKILL.md)
on_complete: S6_priority_watch | S7_oa
"""
from .base import NodeResult


def run(
    case: dict,
    diff_issues: list[str],
    ipr_approved: bool,
    oa_already_received: bool = False,
) -> NodeResult:
    if diff_issues:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="回稿形审发现问题：" + "；".join(diff_issues),
            needs_human=True,
            human_gate="ipr_scope_review",
        )

    if not ipr_approved:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="形审通过，等待 IPR 范围审查",
            needs_human=True,
            human_gate="ipr_scope_review",
        )

    to_node = "S7_oa" if oa_already_received else "S6_priority_watch"
    return NodeResult(
        to_node=to_node,
        evidence="IPR 范围审查通过",
        summary=f"回稿审查通过，进入 {to_node}",
        events=[("s5_pass", "IPR 范围审查通过")],
    )
