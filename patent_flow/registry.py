"""Maps state-machine node names (patent_flow/state_machine.yaml) to their
task-layer handler's `run` function. This is the seam between the state
machine (what's legal) and the node modules (what actually happens);
`workflow.dispatch()` is the only caller."""
from .nodes import (
    s1_mining,
    s2_search,
    s3_disclosure,
    s4_filing,
    s5_review,
    s6_priority,
    s7_oa,
    s8_annuity,
)

NODE_REGISTRY = {
    "S1_mining": s1_mining.run,
    "S2_search": s2_search.run,
    "S3_disclosure": s3_disclosure.run,
    "S4_filing": s4_filing.run,
    "S5_review": s5_review.run,
    "S6_priority_watch": s6_priority.run,
    "S7_oa": s7_oa.run,
    "S8_annuity": s8_annuity.run,
}


def get_handler(node: str):
    try:
        return NODE_REGISTRY[node]
    except KeyError:
        raise ValueError(f"No node handler registered for {node!r}") from None
