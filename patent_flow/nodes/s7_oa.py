"""S7 OA审查 — pull cited references, draft rebuttal arguments.

human_gate: ipr_finalize_response (see skills/task/patent-oa/SKILL.md)
on_complete: S8_annuity
"""
from .base import NodeResult


def run(case: dict, rebuttal_ready: bool, ipr_finalized: bool) -> NodeResult:
    if not rebuttal_ready:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="反驳论点草稿尚未就绪",
            needs_human=True,
            human_gate="ipr_finalize_response",
        )

    if not ipr_finalized:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="反驳论点已就绪，等待 IPR 定稿",
            needs_human=True,
            human_gate="ipr_finalize_response",
        )

    return NodeResult(
        to_node="S8_annuity",
        evidence="IPR 定稿完成",
        summary="OA 答复已定稿并提交，进入授权年费监控",
        events=[("s7_pass", "IPR 定稿完成")],
    )
