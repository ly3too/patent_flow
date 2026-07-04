"""S3 交底 — issue disclosure template, format checks, figure-number consistency.

human_gate: ipr_review_disclosure (see skills/task/patent-disclosure/SKILL.md)
on_complete: S4_filing
"""
from .base import NodeResult

REQUIRED_SECTIONS = ("技术领域", "背景技术", "发明内容", "附图说明", "具体实施方式")


def check_figure_consistency(referenced_figures: set[int], provided_figures: set[int]) -> dict:
    return {
        "missing": sorted(referenced_figures - provided_figures),
        "unused": sorted(provided_figures - referenced_figures),
    }


def run(
    case: dict,
    sections_present,
    referenced_figures,
    provided_figures,
    ipr_approved: bool,
) -> NodeResult:
    # Accept lists too — `run-node`'s CLI passes JSON arrays, not Python sets.
    sections_present = set(sections_present)
    referenced_figures = set(referenced_figures)
    provided_figures = set(provided_figures)

    missing_sections = [s for s in REQUIRED_SECTIONS if s not in sections_present]
    fig_check = check_figure_consistency(referenced_figures, provided_figures)

    issues = []
    if missing_sections:
        issues.append(f"缺少章节：{'、'.join(missing_sections)}")
    if fig_check["missing"]:
        issues.append(f"引用了未提供的附图：{fig_check['missing']}")
    if fig_check["unused"]:
        issues.append(f"提供了未引用的附图：{fig_check['unused']}")

    if issues:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="交底书格式校验未通过：" + "；".join(issues),
            needs_human=True,
            human_gate="ipr_review_disclosure",
        )

    if not ipr_approved:
        return NodeResult(
            to_node=None,
            evidence="",
            summary="交底书格式校验通过，等待 IPR 审核",
            needs_human=True,
            human_gate="ipr_review_disclosure",
        )

    return NodeResult(
        to_node="S4_filing",
        evidence="IPR 审核通过",
        summary="交底书审核通过，进入委案",
        events=[("s3_pass", "IPR 审核通过")],
    )
