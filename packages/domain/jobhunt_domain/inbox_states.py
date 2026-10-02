INBOX_PIPELINE = (
    "captured",
    "normalized",
    "matched",
    "review_required",
    "tailored",
    "ready_to_apply",
    "applied",
)

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "captured": ("normalized",),
    "normalized": ("matched", "review_required"),
    "matched": ("review_required",),
    "review_required": ("tailored", "ready_to_apply"),
    "tailored": ("ready_to_apply", "review_required"),
    "ready_to_apply": ("applied", "review_required"),
    "applied": (),
}


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, ())


def assert_transition(from_state: str, to_state: str) -> None:
    if not can_transition(from_state, to_state):
        raise ValueError(f"illegal inbox transition {from_state} -> {to_state}")
