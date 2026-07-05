from datetime import date

import pytest

from patent_flow.case_no import generate_case_no, is_valid_case_no


class FakeStore:
    """Minimal stand-in for BitableStore: get_case() raises KeyError unless
    the case_no is in `existing`."""

    def __init__(self, existing: set[str] = frozenset()):
        self.existing = set(existing)
        self.lookups = []

    def get_case(self, case_no: str) -> dict:
        self.lookups.append(case_no)
        if case_no in self.existing:
            return {"案号": case_no}
        raise KeyError(case_no)


def test_is_valid_case_no_accepts_new_scheme():
    assert is_valid_case_no("20260705ABCDE")


def test_is_valid_case_no_rejects_old_scheme():
    assert not is_valid_case_no("2026017CNU")


def test_is_valid_case_no_rejects_garbage():
    assert not is_valid_case_no("not-a-case-no")


def test_generate_case_no_has_date_prefix_and_five_letters():
    case_no = generate_case_no(FakeStore(), today=date(2026, 7, 5))
    assert case_no.startswith("20260705")
    assert len(case_no) == 13
    assert case_no[8:].isalpha()
    assert case_no[8:].isupper()


def test_generate_case_no_retries_on_collision(monkeypatch):
    calls = {"n": 0}
    collide_first = "20260705AAAAA"

    def fake_choices(population, k):
        calls["n"] += 1
        return list("AAAAA") if calls["n"] == 1 else list("BBBBB")

    monkeypatch.setattr("patent_flow.case_no.random.choices", fake_choices)

    store = FakeStore(existing={collide_first})
    case_no = generate_case_no(store, today=date(2026, 7, 5))

    assert case_no == "20260705BBBBB"
    assert store.lookups == [collide_first, "20260705BBBBB"]


def test_generate_case_no_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("patent_flow.case_no.random.choices", lambda population, k: list("AAAAA"))
    store = FakeStore(existing={"20260705AAAAA"})
    with pytest.raises(RuntimeError):
        generate_case_no(store, today=date(2026, 7, 5))
