import pytest

from patent_flow.registry import NODE_REGISTRY, get_handler
from patent_flow.state_machine import get_sm


def test_registry_covers_every_state_machine_node():
    sm_nodes = set(get_sm()["states"].keys())
    assert set(NODE_REGISTRY.keys()) == sm_nodes


def test_get_handler_returns_callable():
    handler = get_handler("S1_mining")
    assert callable(handler)


def test_get_handler_rejects_unknown_node():
    with pytest.raises(ValueError, match="No node handler registered"):
        get_handler("S99_nonexistent")
