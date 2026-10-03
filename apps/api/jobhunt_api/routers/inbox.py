from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import approvals as approval_svc
from jobhunt_api.services import audit

router = APIRouter(tags=["inbox"])


class InboxAction(BaseModel):
    action: str
    note: str | None = None


def _item_sql() -> str:
    return """
    SELECT i.id, i.state, i.saved, i.rejected, i.duplicate_of, i.created_at, i.updated_at,
           c.id AS capture_id, c.title, c.company, c.location, c.excerpt, c.source_url, c.canonical_url,
           c.content_hash, c.extracted_emails, c.extracted_apply_urls,
           c.capture_kind, c.captured_at, c.capture_method, c.author,
           j.description AS job_description, j.apply_url,
           m.id AS match_decision_id, m.overall_score, m.confidence, m.breakdown, m.matched_skills, m.missing_skills,
           m.unknown_inputs, m.reasons_to_apply, m.risks, m.freshness_hours, m.hard_filter_reasons,
           m.passed_hard_filters
    FROM inbox_items i
    JOIN source_captures c ON c.id = i.capture_id
    LEFT JOIN jobs j ON j.id = i.job_id
    LEFT JOIN match_decisions m ON m.id = i.match_decision_id
    WHERE i.user_id = %s
    """


def _enrich_item(row: dict, user_id: str) -> dict:
    if not row:
        return row
    item_id = row["id"]
    tasks = db.fetch_all(
        "SELECT id, kind, status, created_at FROM approval_tasks WHERE user_id = %s AND inbox_item_id = %s ORDER BY created_at DESC",
        (user_id, item_id),
    )
    docs = db.fetch_all(
        "SELECT id, kind, status, fact_gate_passed, version, content FROM tailored_documents WHERE user_id = %s AND inbox_item_id = %s",
        (user_id, item_id),
    )
    excerpt = row.get("excerpt") or ""
    desc = row.get("job_description") or ""
    row["captured_text"] = desc if len(desc) > len(excerpt) else excerpt
    row["approval_tasks"] = tasks
    row["documents"] = docs
    return row


@router.get("/inbox")
def list_inbox(user: dict = Depends(current_user)) -> dict:
    rows = db.fetch_all(
        _item_sql() + " AND i.rejected = false ORDER BY m.overall_score DESC NULLS LAST, i.created_at DESC",
        (user["user_id"],),
    )
    return {"items": [_enrich_item(r, user["user_id"]) for r in rows]}


@router.get("/inbox/{item_id}")
def get_inbox(item_id: str, user: dict = Depends(current_user)) -> dict:
    row = db.fetch_one(_item_sql() + " AND i.id = %s", (user["user_id"], item_id))
    if not row:
        raise HTTPException(404, "not found")
    return {"item": _enrich_item(row, user["user_id"])}


@router.post("/inbox/{item_id}/actions")
def act(item_id: str, body: InboxAction, user: dict = Depends(current_user)) -> dict:
    row = db.fetch_one("SELECT id, state FROM inbox_items WHERE id = %s AND user_id = %s", (item_id, user["user_id"]))
    if not row:
        raise HTTPException(404, "not found")
    state = row["state"]
    if body.action == "reject":
        db.execute("UPDATE inbox_items SET rejected = true, updated_at = now() WHERE id = %s AND user_id = %s", (item_id, user["user_id"]))
        db.execute(
            "INSERT INTO feedback_events (user_id, inbox_item_id, signal) VALUES (%s, %s, 'reject')",
            (user["user_id"], item_id),
        )
    elif body.action == "save":
        db.execute("UPDATE inbox_items SET saved = true, updated_at = now() WHERE id = %s AND user_id = %s", (item_id, user["user_id"]))
        db.execute(
            "INSERT INTO feedback_events (user_id, inbox_item_id, signal) VALUES (%s, %s, 'save')",
            (user["user_id"], item_id),
        )
    elif body.action == "request_analysis":
        if state != "review_required":
            raise HTTPException(409, "analysis can only be requested from review_required")
        db.execute(
            "INSERT INTO approval_tasks (user_id, inbox_item_id, kind, status, payload) VALUES (%s, %s, %s, 'pending', '{}'::jsonb)",
            (user["user_id"], item_id, body.action),
        )
    elif body.action == "prepare_application":
        if state != "review_required":
            raise HTTPException(409, "prepare_application requires review_required")
        db.execute(
            "INSERT INTO approval_tasks (user_id, inbox_item_id, kind, status, payload) VALUES (%s, %s, %s, 'pending', '{}'::jsonb)",
            (user["user_id"], item_id, "prepare_application"),
        )
    elif body.action == "request_draft_approval":
        if state != "tailored":
            raise HTTPException(409, "draft approval requires tailored state")
        approval_svc.create_draft_approval_task(user["user_id"], item_id)
    else:
        raise HTTPException(400, "unknown action")
    audit.record(user["user_id"], f"inbox_{body.action}", "inbox_item", item_id)
    return get_inbox(item_id, user)


@router.post("/inbox/{item_id}/handoff")
def handoff_apply(item_id: str, user: dict = Depends(current_user)) -> dict:
    row = db.fetch_one(
        """
        SELECT i.state, c.extracted_apply_urls, j.apply_url, c.source_url
        FROM inbox_items i
        JOIN source_captures c ON c.id = i.capture_id
        LEFT JOIN jobs j ON j.id = i.job_id
        WHERE i.id = %s AND i.user_id = %s
        """,
        (item_id, user["user_id"]),
    )
    if not row:
        raise HTTPException(404, "not found")
    if row["state"] != "ready_to_apply":
        raise HTTPException(400, "inbox item not ready_to_apply")
    urls = list(row.get("extracted_apply_urls") or [])
    if row.get("apply_url"):
        urls.insert(0, row["apply_url"])
    if not urls and row.get("source_url"):
        urls = [row["source_url"]]
    audit.record(user["user_id"], "external_apply_opened", "inbox_item", item_id, {"urls": urls})
    return {"apply_urls": urls, "handoff": "open_in_browser_only"}
