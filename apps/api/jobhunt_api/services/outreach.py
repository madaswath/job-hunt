import uuid

from jobhunt_agents.permissions import assert_agent_permission

from jobhunt_api import db
from jobhunt_api.services import agents, audit


def create_outreach_draft(
    user_id: str,
    *,
    inbox_item_id: str,
    channel: str = "email",
    body: str | None = None,
    explicit_request: bool = True,
) -> dict:
    assert_agent_permission(
        "krishna",
        "create_outreach_draft",
        {"explicit_outreach_request": explicit_request},
    )
    item = db.fetch_one(
        """
        SELECT i.id, c.title, c.company
        FROM inbox_items i
        JOIN source_captures c ON c.id = i.capture_id
        WHERE i.id = %s AND i.user_id = %s
        """,
        (inbox_item_id, user_id),
    )
    if not item:
        raise ValueError("inbox item not found")
    if not body:
        body = (
            f"Hello,\n\nI am interested in the {item['title']} role at {item['company']}. "
            "Please find my resume attached. I would welcome a brief conversation.\n\nThank you."
        )
    draft_id = str(uuid.uuid4())
    ctx = {"explicit_outreach_request": explicit_request}
    started = agents.start_run(
        user_id,
        "krishna",
        "create_outreach_draft",
        {"inbox_item_id": inbox_item_id},
        context=ctx,
    )
    db.execute(
        """
        INSERT INTO outreach_drafts (id, user_id, inbox_item_id, channel, body, status)
        VALUES (%s, %s, %s, %s, %s, 'candidate_review')
        """,
        (draft_id, user_id, inbox_item_id, channel, body),
    )
    agents.finish_run(user_id, started, {"draft_id": draft_id})
    audit.record(user_id, "outreach_draft_created", "outreach_draft", draft_id, {"channel": channel, "never_send": True})
    row = db.fetch_one("SELECT * FROM outreach_drafts WHERE id = %s", (draft_id,))
    return dict(row)
