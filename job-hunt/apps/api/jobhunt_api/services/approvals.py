
from jobhunt_api import db
from jobhunt_api.services import audit, documents
from jobhunt_api.services.inbox_transitions import transition_inbox


def list_pending(user_id: str) -> list[dict]:
    return db.fetch_all(
        "SELECT * FROM approval_tasks WHERE user_id = %s AND status = 'pending' ORDER BY created_at DESC",
        (user_id,),
    )


def decide(user_id: str, task_id: str, decision: str) -> dict:
    task = db.fetch_one(
        "SELECT * FROM approval_tasks WHERE id = %s AND user_id = %s",
        (task_id, user_id),
    )
    if not task:
        raise ValueError("approval task not found")
    if task["status"] != "pending":
        raise ValueError("task already decided")
    if decision not in {"approved", "denied"}:
        raise ValueError("invalid decision")

    db.execute(
        "UPDATE approval_tasks SET status = %s, decided_at = now() WHERE id = %s AND user_id = %s",
        (decision, task_id, user_id),
    )
    audit.record(user_id, f"approval_{decision}", "approval_task", task_id, {"kind": task["kind"]})

    inbox_id = str(task["inbox_item_id"]) if task.get("inbox_item_id") else None
    result: dict = {"task_id": task_id, "status": decision}

    if decision == "denied" or not inbox_id:
        return result

    kind = task["kind"]
    item = db.fetch_one("SELECT state FROM inbox_items WHERE id = %s AND user_id = %s", (inbox_id, user_id))
    if not item:
        return result

    if kind == "prepare_application":
        gen = documents.generate_drafts_for_inbox(user_id, inbox_id, task_id)
        result["documents"] = gen["documents"]
        result["inbox_state"] = db.fetch_one("SELECT state FROM inbox_items WHERE id = %s", (inbox_id,))["state"]
    elif kind == "approve_draft":
        docs = db.fetch_all(
            "SELECT fact_gate_passed FROM tailored_documents WHERE inbox_item_id = %s AND user_id = %s",
            (inbox_id, user_id),
        )
        if not docs or not all(d["fact_gate_passed"] for d in docs):
            raise PermissionError("dharma gate not passed for all documents")
        if item["state"] == "tailored":
            transition_inbox(user_id, inbox_id, "tailored", "ready_to_apply", "candidate_approved_draft", task_id)
        result["inbox_state"] = "ready_to_apply"
    elif kind == "request_analysis":
        pass  # Brihaspati planned — task approved but no analysis run

    return result


def create_draft_approval_task(user_id: str, inbox_item_id: str) -> str:
    row = db.fetch_one(
        """
        INSERT INTO approval_tasks (user_id, inbox_item_id, kind, status, payload)
        VALUES (%s, %s, 'approve_draft', 'pending', '{}'::jsonb)
        RETURNING id
        """,
        (user_id, inbox_item_id),
    )
    audit.record(user_id, "approval_requested", "approval_task", str(row["id"]), {"kind": "approve_draft"})
    return str(row["id"])
