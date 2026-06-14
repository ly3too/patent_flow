from pathlib import Path
import yaml

_YAML_PATH = Path(__file__).parent / "state_machine.yaml"

def _load() -> dict:
    with open(_YAML_PATH) as f:
        return yaml.safe_load(f)

_SM: dict | None = None

def get_sm() -> dict:
    global _SM
    if _SM is None:
        _SM = _load()
    return _SM

def allowed_transitions(current_node: str) -> list[str]:
    sm = get_sm()
    state = sm["states"].get(current_node)
    if state is None:
        raise ValueError(f"Unknown state: {current_node}")
    return state.get("on_complete", [])

def validate_transition(from_node: str, to_node: str) -> None:
    allowed = allowed_transitions(from_node)
    if to_node not in allowed:
        raise ValueError(
            f"Illegal transition {from_node} → {to_node}. "
            f"Allowed: {allowed}"
        )
