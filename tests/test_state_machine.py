import pytest
from patent_flow.state_machine import allowed_transitions, validate_transition


def test_s1_only_goes_to_s2():
    assert allowed_transitions("S1_mining") == ["S2_search"]


def test_s2_can_terminate():
    assert "TERMINATED" in allowed_transitions("S2_search")
    assert "S3_disclosure" in allowed_transitions("S2_search")


def test_illegal_transition_raises():
    with pytest.raises(ValueError, match="Illegal transition"):
        validate_transition("S1_mining", "S8_annuity")


def test_legal_transition_passes():
    validate_transition("S1_mining", "S2_search")


def test_unknown_state_raises():
    with pytest.raises(ValueError, match="Unknown state"):
        allowed_transitions("S99_nonexistent")


def test_full_happy_path_reachable():
    happy_path = [
        ("S1_mining", "S2_search"),
        ("S2_search", "S3_disclosure"),
        ("S3_disclosure", "S4_filing"),
        ("S4_filing", "S5_review"),
        ("S5_review", "S6_priority_watch"),
        ("S6_priority_watch", "S7_oa"),
        ("S7_oa", "S8_annuity"),
        ("S8_annuity", "DONE"),
    ]
    for from_node, to_node in happy_path:
        validate_transition(from_node, to_node)
