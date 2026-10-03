"""Applications tracker: record handoff / outcomes without auto-submit."""

from __future__ import annotations

from jobhunt_domain.application_states import APPLICATION_STATES, assert_transition

from jobhunt_api import db
from jobhunt_api.services import audit
from jobhunt_api.services.inbox_transitions import transition_inbox


def _enrich(row: dict) -> dict:
    if not row:
        return row
    return {
        "id": str(row["id"]),
        "inbox_item_id": str(row["inbox_item_id"]) if row.get("inbox_item_id") else None,
        "state": row["state"],
        "apply_url": row.get("apply_url"),
        "notes": row.get("notes"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "title": row.get("title"),
        "company": row.get("company"),
        "location": row.get("location"),
        "source_url": row.get("source_url"),
        "overall_score": row.get("overall_score"),
    }


def list_applications(user_id: str) -> list[dict]:
    rows = db.fetch_all(
        """
        SELECT a.id, a.inbox_item_id, a.state, a.apply_url, a.notes, a.created_at, a.updated_at,
               c.title, c.company, c.location, c.source_url,
               m.overall_score
        FROM applications a
        LEFT JOIN inbox_items i ON i.id = a.inbox_item_id
        LEFT JOIN source_captures c ON c.id = i.capture_id
        LEFT JOIN match_decisions m ON m.id = i.match_decision_id
        WHERE a.user_id = %s
        ORDER BY a.updated_at DESC
        """,
        (user_id,),
    )
    return [_enrich(r) for r in rows]


def counts_by_stage(user_id: str) -> dict[str, int]:
    rows = db.fetch_all(
        "SELECT state, count(*)::int AS n FROM applications WHERE user_id = %s GROUP BY state",
        (user_id,),
    )
    out = {s: 0 for s in APPLICATION_STATES}
    for r in rows:
        out[r["state"]] = r["n"]
    return out


def get_application(user_id: str, application_id: str) -> dict | None:
    row = db.fetch_one(
        """
        SELECT a.id, a.inbox_item_id, a.state, a.apply_url, a.notes, a.created_at, a.updated_at,
               c.title, c.company, c.location, c.source_url,
               m.overall_score
        FROM applications a
        LEFT JOIN inbox_items i ON i.id = a.inbox_item_id
        LEFT JOIN source_captures c ON c.id = i.capture_id
        LEFT JOIN match_decisions m ON m.id = i.match_decision_id
        WHERE a.id = %s AND a.user_id = %s
        """,
        (application_id, user_id),
    )
    return _enrich(row) if row else None


def _record_event(user_id: str, application_id: str, from_state: str | None, to_state: str, note: str | None) -> None:
    db.execute(
        """
        INSERT INTO application_events (user_id, application_id, from_state, to_state, note)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, application_id, from_state, to_state, note),
    )


def create_or_get_from_inbox(
    user_id: str,
    inbox_item_id: str,
    *,
    apply_url: str | None = None,
    notes: str | None = None,
    mark_inbox_applied: bool = False,
) -> dict:
    """Start tracking after candidate opens apply / confirms intent. Never submits."""
    owned = db.fetch_one(
        "SELECT id FROM inbox_items WHERE id = %s AND user_id = %s",
        (inbox_item_id, user_id),
    )
    if not owned:
        raise LookupError("inbox item not found")

    existing = db.fetch_one(
        "SELECT id FROM applications WHERE user_id = %s AND inbox_item_id = %s",
        (user_id, inbox_item_id),
    )
    if existing:
        app = get_application(user_id, str(existing["id"]))
        assert app is not None
        return app

    row = db.fetch_one(
        """
        INSERT INTO applications (user_id, inbox_item_id, state, apply_url, notes)
        VALUES (%s, %s, 'started', %s, %s)
        RETURNING id
        """,
        (user_id, inbox_item_id, apply_url, notes),
    )
    app_id = str(row["id"])
    _record_event(user_id, app_id, None, "started", notes or "application_started")
    audit.record(
        user_id,
        "application_started",
        "application",
        app_id,
        {"inbox_item_id": inbox_item_id, "apply_url": apply_url},
    )

    if mark_inbox_applied:
        item = db.fetch_one(
            "SELECT state FROM inbox_items WHERE id = %s AND user_id = %s",
            (inbox_item_id, user_id),
        )
        if item and item["state"] == "ready_to_apply":
            approval = db.fetch_one(
                """
                SELECT id FROM approval_tasks
                WHERE user_id = %s AND inbox_item_id = %s AND status = 'approved'
                ORDER BY decided_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (user_id, inbox_item_id),
            )
            if approval:
                transition_inbox(
                    user_id,
                    inbox_item_id,
                    "ready_to_apply",
                    "applied",
                    "candidate_handoff",
                    str(approval["id"]),
                )

    app = get_application(user_id, app_id)
    assert app is not None
    return app


def update_state(user_id: str, application_id: str, to_state: str, note: str | None = None) -> dict:
    if to_state not in APPLICATION_STATES:
        raise ValueError(f"unknown application state {to_state}")
    row = db.fetch_one(
        "SELECT id, state FROM applications WHERE id = %s AND user_id = %s",
        (application_id, user_id),
    )
    if not row:
        raise LookupError("application not found")
    from_state = row["state"]
    assert_transition(from_state, to_state)
    if from_state == to_state and not note:
        app = get_application(user_id, application_id)
        assert app is not None
        return app
    db.execute(
        """
        UPDATE applications
        SET state = %s, notes = COALESCE(%s, notes), updated_at = now()
        WHERE id = %s AND user_id = %s
        """,
        (to_state, note, application_id, user_id),
    )
    _record_event(user_id, application_id, from_state, to_state, note)
    audit.record(
        user_id,
        "application_state_changed",
        "application",
        application_id,
        {"from": from_state, "to": to_state},
    )
    app = get_application(user_id, application_id)
    assert app is not None
    return app
