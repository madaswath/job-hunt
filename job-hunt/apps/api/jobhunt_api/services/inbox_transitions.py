from jobhunt_agents.permissions import assert_agent_permission
from jobhunt_domain.inbox_states import assert_transition

from jobhunt_api import db
from jobhunt_api.services import audit


def transition_inbox(
    user_id: str,
    inbox_id: str,
    from_state: str,
    to_state: str,
    reason: str,
    approval_id: str | None = None,
) -> None:
    ctx = {"to_state": to_state, "approval_id": approval_id, "bypass_approval": False}
    assert_agent_permission("vishwakarma", "transition_inbox", ctx)
    assert_transition(from_state, to_state)
    db.execute(
        "UPDATE inbox_items SET state = %s, updated_at = now() WHERE id = %s AND user_id = %s",
        (to_state, inbox_id, user_id),
    )
    db.execute(
        """
        INSERT INTO inbox_state_events (user_id, inbox_item_id, from_state, to_state, reason)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, inbox_id, from_state, to_state, reason),
    )
    audit.record(
        user_id,
        "inbox_transition",
        "inbox_item",
        inbox_id,
        {"from": from_state, "to": to_state, "approval_id": approval_id},
    )
