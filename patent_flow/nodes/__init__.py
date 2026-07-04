"""Node handlers for the 8-node patent lifecycle state machine.

Each module exposes a single `run(case: dict) -> dict` entry point that the
task-layer skill for that node calls after `load_case`. Handlers never write
state directly — they return a proposed `(to_node, evidence)` for the
top-level workflow skill to pass into `patent_flow.transition.transition()`.
"""
