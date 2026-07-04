from datetime import date

import pytest

from patent_flow.nodes import (
    s1_mining,
    s2_search,
    s3_disclosure,
    s4_filing,
    s5_review,
    s6_priority,
    s7_oa,
    s8_annuity,
)


# --- S1 mining -------------------------------------------------------------

def test_s1_missing_elements_stays_put():
    result = s1_mining.run({}, three_elements={"技术问题": "x"}, ipr_confirmed=True)
    assert result.to_node is None
    assert result.needs_human
    assert result.human_gate == "ipr_confirm_three_elements"


def test_s1_waits_for_ipr_confirmation():
    complete = {"技术问题": "a", "技术方案": "b", "技术效果": "c"}
    result = s1_mining.run({}, three_elements=complete, ipr_confirmed=False)
    assert result.to_node is None
    assert result.needs_human


def test_s1_confirmed_advances_to_s2():
    complete = {"技术问题": "a", "技术方案": "b", "技术效果": "c"}
    result = s1_mining.run({}, three_elements=complete, ipr_confirmed=True)
    assert result.to_node == "S2_search"
    assert result.events


# --- S2 search --------------------------------------------------------------

def test_s2_terminates_on_no_novelty():
    result = s2_search.run({}, ipr_verdict="无新创性", evidence="对比文件 CN123 方案雷同")
    assert result.to_node == "TERMINATED"


def test_s2_advances_on_novelty():
    result = s2_search.run({}, ipr_verdict="有新创性")
    assert result.to_node == "S3_disclosure"


def test_s2_rejects_unknown_verdict():
    with pytest.raises(ValueError):
        s2_search.run({}, ipr_verdict="不知道")


def test_build_search_query_joins_elements():
    q = s2_search.build_search_query({"技术问题": "松动", "技术方案": "卡扣", "技术效果": ""})
    assert q == "松动 卡扣"


# --- S3 disclosure ------------------------------------------------------------

def test_s3_flags_missing_sections_and_figures():
    result = s3_disclosure.run(
        {},
        sections_present={"技术领域", "背景技术"},
        referenced_figures={1, 2, 3},
        provided_figures={1, 2},
        ipr_approved=True,
    )
    assert result.to_node is None
    assert "缺少章节" in result.summary
    assert "引用了未提供的附图" in result.summary


def test_s3_clean_but_unapproved_waits():
    all_sections = set(s3_disclosure.REQUIRED_SECTIONS)
    result = s3_disclosure.run(
        {}, sections_present=all_sections, referenced_figures={1}, provided_figures={1}, ipr_approved=False
    )
    assert result.to_node is None
    assert result.needs_human


def test_s3_clean_and_approved_advances():
    all_sections = set(s3_disclosure.REQUIRED_SECTIONS)
    result = s3_disclosure.run(
        {}, sections_present=all_sections, referenced_figures={1}, provided_figures={1}, ipr_approved=True
    )
    assert result.to_node == "S4_filing"


def test_s3_accepts_json_lists_not_just_sets():
    # tools/run_node.sh passes JSON arrays (Python lists), not sets.
    result = s3_disclosure.run(
        {},
        sections_present=list(s3_disclosure.REQUIRED_SECTIONS),
        referenced_figures=[1, 2],
        provided_figures=[1, 2],
        ipr_approved=True,
    )
    assert result.to_node == "S4_filing"


# --- S4 filing (fully automatic) --------------------------------------------

def test_s4_rejects_bad_case_no():
    with pytest.raises(ValueError):
        s4_filing.run({"案号": "bad-case-no"})


def test_s4_auto_advances_to_s5():
    result = s4_filing.run({"案号": "2026017CNU", "案件名": "电视挂架自适应卡扣"})
    assert result.to_node == "S5_review"
    assert "案号：2026017CNU" in result.extra["filing_email_draft"]


# --- S5 review ---------------------------------------------------------------

def test_s5_flags_diff_issues():
    result = s5_review.run({}, diff_issues=["错别字x3"], ipr_approved=True)
    assert result.to_node is None


def test_s5_routes_to_priority_watch_by_default():
    result = s5_review.run({}, diff_issues=[], ipr_approved=True)
    assert result.to_node == "S6_priority_watch"


def test_s5_routes_to_oa_when_already_received():
    result = s5_review.run({}, diff_issues=[], ipr_approved=True, oa_already_received=True)
    assert result.to_node == "S7_oa"


# --- S6 priority watch ---------------------------------------------------------

def test_s6_priority_deadline_is_ten_months_after_filing():
    case = {"申请日": "2026-01-15"}
    assert s6_priority.priority_deadline(case) == date(2026, 11, 15)


def test_s6_silent_when_no_tier_hit():
    case = {"申请日": "2026-01-01"}
    result = s6_priority.run(case, today=date(2026, 1, 2))
    assert result.to_node is None
    assert not result.needs_human


def test_s6_reminds_on_exact_tier_day():
    deadline = s6_priority.priority_deadline({"申请日": "2026-01-01"})
    today = date.fromordinal(deadline.toordinal() - 30)
    result = s6_priority.run({"申请日": "2026-01-01"}, today=today)
    assert result.needs_human
    assert result.human_gate == "pm_priority_decision"


def test_s6_escalates_at_final_tier():
    deadline = s6_priority.priority_deadline({"申请日": "2026-01-01"})
    today = date.fromordinal(deadline.toordinal() - s6_priority.ESCALATE_AT)
    result = s6_priority.run({"申请日": "2026-01-01"}, today=today)
    assert "升级" in result.summary


def test_s6_pm_decision_advances_to_s7():
    result = s6_priority.run({}, today=date(2026, 1, 1), pm_decision="申请美国")
    assert result.to_node == "S7_oa"


def test_s6_rejects_unknown_decision():
    with pytest.raises(ValueError):
        s6_priority.run({}, today=date(2026, 1, 1), pm_decision="随便")


# --- S7 OA ---------------------------------------------------------------------

def test_s7_waits_for_rebuttal():
    result = s7_oa.run({}, rebuttal_ready=False, ipr_finalized=False)
    assert result.to_node is None


def test_s7_waits_for_ipr_finalization():
    result = s7_oa.run({}, rebuttal_ready=True, ipr_finalized=False)
    assert result.to_node is None
    assert result.needs_human


def test_s7_advances_to_s8():
    result = s7_oa.run({}, rebuttal_ready=True, ipr_finalized=True)
    assert result.to_node == "S8_annuity"


# --- S8 annuity ------------------------------------------------------------------

def test_s8_silent_when_no_tier_hit():
    case = {"年费到期日": "2026-12-31"}
    result = s8_annuity.run(case, today=date(2026, 1, 1))
    assert result.to_node is None
    assert not result.needs_human


def test_s8_reminds_on_exact_tier_day():
    case = {"年费到期日": "2026-12-31"}
    result = s8_annuity.run(case, today=date(2026, 10, 2))  # 90 days before
    assert result.needs_human
    assert result.human_gate == "pm_maintain_decision"


def test_s8_maintain_decision_completes_case():
    result = s8_annuity.run({"案号": "2026017CNU"}, today=date(2026, 1, 1), pm_decision="继续缴费")
    assert result.to_node == "DONE"
    assert "payment_email_draft" in result.extra


def test_s8_abandon_decision_completes_case():
    result = s8_annuity.run({"案号": "2026017CNU"}, today=date(2026, 1, 1), pm_decision="放弃维持")
    assert result.to_node == "DONE"


def test_s8_rejects_unknown_decision():
    with pytest.raises(ValueError):
        s8_annuity.run({}, today=date(2026, 1, 1), pm_decision="随便")
