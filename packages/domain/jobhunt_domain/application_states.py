"""Post-handoff application tracker states (candidate-controlled)."""

APPLICATION_STATES = (
    "started",
    "applied",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
)

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "started": ("applied", "interview", "rejected", "withdrawn"),
    "applied": ("interview", "offer", "rejected", "withdrawn"),
    "interview": ("offer", "rejected", "withdrawn"),
    "offer": ("rejected", "withdrawn"),
    "rejected": (),
    "withdrawn": (),
}


def can_transition(from_state: str, to_state: str) -> bool:
    if from_state == to_state:
        return True
    return to_state in ALLOWED_TRANSITIONS.get(from_state, ())


def assert_transition(from_state: str, to_state: str) -> None:
    if not can_transition(from_state, to_state):
        raise ValueError(f"illegal application transition {from_state} -> {to_state}")
