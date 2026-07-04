"""S2 查新 — generate search queries, call prior-art search, produce feature diff table.

human_gate: ipr_decide_continue (see skills/task/patent-search/SKILL.md)
on_complete: S3_disclosure | TERMINATED
"""
from .base import NodeResult

VALID_VERDICTS = {"有新创性", "无新创性"}


def build_search_query(three_elements: dict) -> str:
    """Deterministic keyword join from the three elements — a starting point
    for the actual search tool, not a substitute for it."""
    return " ".join(v for v in three_elements.values() if v)


def run(
    case: dict,
    ipr_verdict: str,
    evidence: str = "",
    feature_diff: list[dict] | None = None,
) -> NodeResult:
    if ipr_verdict not in VALID_VERDICTS:
        raise ValueError(f"未知查新判定 {ipr_verdict!r}，应为 {VALID_VERDICTS}")

    if ipr_verdict == "无新创性":
        return NodeResult(
            to_node="TERMINATED",
            evidence=evidence or "无新创性",
            summary="案件终止：与对比文件差异不足以构成新创性",
            events=[("s2_terminate", evidence or "无新创性")],
            extra={"feature_diff": feature_diff or []},
        )

    return NodeResult(
        to_node="S3_disclosure",
        evidence=evidence or "有新创性，可继续申请",
        summary="查新通过，进入交底阶段",
        events=[("s2_pass", evidence or "有新创性")],
        extra={"feature_diff": feature_diff or []},
    )
