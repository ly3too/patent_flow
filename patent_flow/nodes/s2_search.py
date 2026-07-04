"""S2 查新 — generate search queries, call prior-art search, produce feature diff table.

human_gate: ipr_decide_continue (see skills/task/patent-search/SKILL.md)
on_complete: S3_disclosure | TERMINATED
"""


def run(case: dict) -> dict:
    raise NotImplementedError("S2 search handler not yet implemented")
