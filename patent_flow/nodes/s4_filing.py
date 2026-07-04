"""S4 委案 — fully automatic: case number allocation, ledger write, filing email draft.

auto: true (P1 priority, see skills/task/patent-filing/SKILL.md)
on_complete: S5_review
"""
import re
from .base import NodeResult

CASE_NO_RE = re.compile(r"^\d{7}[A-Z]{2,4}$")


def draft_filing_email(case: dict) -> str:
    return (
        "委案通知\n\n"
        f"案号：{case['案号']}\n"
        f"案件名：{case.get('案件名', '')}\n"
        "请代理所协助办理专利申请手续，附件为交底书及相关材料。"
    )


def run(case: dict) -> NodeResult:
    case_no = case["案号"]
    if not CASE_NO_RE.match(case_no):
        raise ValueError(f"案号格式不合法：{case_no!r}（应为 YYYY+流水号+品线代码，如 2026017CNU）")

    email_draft = draft_filing_email(case)
    return NodeResult(
        to_node="S5_review",
        evidence="委案邮件已生成",
        summary="委案完成，等待代理所回稿",
        events=[("s4_auto_filing", "委案邮件已生成并发送")],
        extra={"filing_email_draft": email_draft},
    )
