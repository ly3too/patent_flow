"""Case number scheme: YYYYMMDD + 5 random uppercase letters.

`generate_case_no()` retries against the ledger on collision; `is_valid_case_no()`
is the pure format check shared by anything that needs to sanity-check an
existing 案号 without generating a new one (e.g. `nodes/s4_filing.py`).
"""
import random
import re
import string
from datetime import date

CASE_NO_RE = re.compile(r"^\d{8}[A-Z]{5}$")

_LETTERS = string.ascii_uppercase
_SUFFIX_LENGTH = 5
_MAX_ATTEMPTS = 20


def is_valid_case_no(case_no: str) -> bool:
    return bool(CASE_NO_RE.match(case_no))


def generate_case_no(store, today: date | None = None) -> str:
    """`store` needs a `get_case(case_no)` that raises `KeyError` when the
    case doesn't exist yet (i.e. a `store.BitableStore`). Retries on
    collision against the live ledger rather than assuming randomness is
    enough."""
    prefix = (today or date.today()).strftime("%Y%m%d")
    for _ in range(_MAX_ATTEMPTS):
        candidate = prefix + "".join(random.choices(_LETTERS, k=_SUFFIX_LENGTH))
        try:
            store.get_case(candidate)
        except KeyError:
            return candidate
    raise RuntimeError(f"未能在 {_MAX_ATTEMPTS} 次尝试内生成不重复的案号")
