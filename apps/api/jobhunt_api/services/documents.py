import uuid

from jobhunt_agents.permissions import assert_agent_permission
from jobhunt_tailoring.fact_gate import fact_gate
from jobhunt_tailoring.templates import build_application_answers, build_cover_letter, build_cv_variant

from jobhunt_api import db
from jobhunt_api.services import agents, audit
from jobhunt_api.services.inbox_transitions import transition_inbox
from jobhunt_api.services.profile_loader import load_verified_fact_values, profile_bits_for_gate
from jobhunt_api.settings import settings


def generate_drafts_for_inbox(user_id: str, inbox_item_id: str, approval_id: str) -> dict:
    if not settings.feature_document_drafts:
        raise PermissionError("document drafts disabled by feature flag")
    assert_agent_permission("saraswati", "generate_document", {"approval_id": approval_id})
    task = db.fetch_one(
        "SELECT id, kind, status, inbox_item_id FROM approval_tasks WHERE id = %s AND user_id = %s",
        (approval_id, user_id),
    )
    if not task:
        raise ValueError("approval task not found")
    if task["kind"] != "prepare_application":
        raise PermissionError("invalid approval task kind for document generation")

    item = db.fetch_one(
        """
        SELECT i.id, i.state, i.capture_id, c.title, c.company, c.excerpt
        FROM inbox_items i
        JOIN source_captures c ON c.id = i.capture_id
        WHERE i.id = %s AND i.user_id = %s
        """,
        (inbox_item_id, user_id),
    )
    if not item:
        raise ValueError("inbox item not found")
    if str(task["inbox_item_id"]) != inbox_item_id:
        raise PermissionError("approval task does not match inbox item")
    profile = db.fetch_one("SELECT full_name, headline FROM candidate_profiles WHERE user_id = %s", (user_id,))
    facts = load_verified_fact_values(user_id)
    title = item.get("title") or "Role"
    company = item.get("company") or ""
    excerpt = item.get("excerpt") or ""
    bits = profile_bits_for_gate(user_id) + [title, company, excerpt]

    s_run = agents.start_run(user_id, "saraswati", "generate_document", {"inbox_item_id": inbox_item_id})
    cv = build_cv_variant(profile.get("full_name") if profile else "", profile.get("headline") if profile else "", facts, title, company)
    cover = build_cover_letter(profile.get("full_name") if profile else "", facts, title, company, excerpt)
    answers = build_application_answers(facts, title)
    agents.finish_run(user_id, s_run, {"kinds": ["cv_variant", "cover_letter", "application_answers"]})

    docs = []
    for kind, content in [("cv_variant", cv), ("cover_letter", cover), ("application_answers", answers)]:
        d_run = agents.start_run(user_id, "dharma", "fact_gate", {"kind": kind})
        gate = fact_gate(content, facts, bits)
        agents.finish_run(user_id, d_run, gate)
        status = "ready" if gate["passed"] else "blocked"
        doc_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO tailored_documents (id, user_id, inbox_item_id, kind, status, content, fact_gate_passed)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (doc_id, user_id, inbox_item_id, kind, status, content, gate["passed"]),
        )
        docs.append({"id": doc_id, "kind": kind, "status": status, "fact_gate_passed": gate["passed"]})

    all_pass = all(d["fact_gate_passed"] for d in docs)
    if all_pass and item["state"] == "review_required":
        transition_inbox(user_id, inbox_item_id, "review_required", "tailored", "dharma_passed", approval_id)
    audit.record(user_id, "documents_generated", "inbox_item", inbox_item_id, {"approval_id": approval_id, "all_pass": all_pass})
    return {"documents": docs, "all_pass": all_pass}


def list_documents(user_id: str, inbox_item_id: str | None = None) -> list[dict]:
    if inbox_item_id:
        return db.fetch_all(
            "SELECT * FROM tailored_documents WHERE user_id = %s AND inbox_item_id = %s ORDER BY created_at DESC",
            (user_id, inbox_item_id),
        )
    return db.fetch_all(
        "SELECT * FROM tailored_documents WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
        (user_id,),
    )
