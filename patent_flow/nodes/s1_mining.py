"""S1 挖掘 — draft the three technical elements from disclosure meeting notes.

human_gate: ipr_confirm_three_elements (see skills/task/patent-mining/SKILL.md)
on_complete: S2_search
"""
from .base import NodeResult

REQUIRED_ELEMENT_KEYS = ("技术问题", "技术方案", "技术效果")


def run(
    case: dict,
    three_elements: dict,
    ipr_confirmed: bool,
    clarifying_questions: list[str] | None = None,
) -> NodeResult:
    missing = [k for k in REQUIRED_ELEMENT_KEYS if not three_elements.get(k)]
    if missing:
        return NodeResult(
            to_node=None,
            evidence="",
            summary=f"技术三要素草稿缺失：{'、'.join(missing)}",
            needs_human=True,
            human_gate="ipr_confirm_three_elements",
        )

    if not ipr_confirmed:
        qs = clarifying_questions or []
        summary = "三要素草稿已完成，等待 IPR 确认"
        if qs:
            summary += f"；待澄清问题 {len(qs)} 个：{'；'.join(qs)}"
        return NodeResult(
            to_node=None,
            evidence="",
            summary=summary,
            needs_human=True,
            human_gate="ipr_confirm_three_elements",
        )

    return NodeResult(
        to_node="S2_search",
        evidence="IPR 确认三要素完整",
        summary="三要素已确认，进入查新",
        events=[("s1_complete", "IPR 确认三要素完整")],
    )
