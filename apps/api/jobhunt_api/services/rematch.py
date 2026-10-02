import json
import uuid

from jobhunt_domain.matching import score_match_v2
from jobhunt_domain.schemas import JobPosting

from jobhunt_api import db
from jobhunt_api.services import agents
from jobhunt_api.services.profile_loader import load_candidate_profile
from jobhunt_api.settings import settings


def enqueue_rematch(user_id: str) -> str:
    key = f"rematch-{user_id}-{uuid.uuid4()}"
    row = db.fetch_one(
        """
        INSERT INTO scan_jobs (user_id, connector_id, payload, idempotency_key)
        VALUES (%s, 'rematch', %s::jsonb, %s)
        RETURNING id
        """,
        (user_id, json.dumps({"rematch": True}), key),
    )
    return str(row["id"])


def rematch_user_captures(user_id: str) -> dict:
    profile = load_candidate_profile(user_id)
    captures = db.fetch_all(
        "SELECT id FROM source_captures WHERE user_id = %s ORDER BY captured_at DESC",
        (user_id,),
    )
    updated = 0
    for cap in captures:
        if _rematch_capture(user_id, str(cap["id"]), profile):
            updated += 1
    return {"rematched": updated, "total": len(captures)}


def _job_posting_from_capture(user_id: str, capture_id: str) -> JobPosting | None:
    job = db.fetch_one("SELECT * FROM jobs WHERE user_id = %s AND capture_id = %s", (user_id, capture_id))
    cap = db.fetch_one("SELECT * FROM source_captures WHERE id = %s AND user_id = %s", (capture_id, user_id))
    if not cap:
        return None
    raw = cap.get("raw_payload") or {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    if job:
        return JobPosting(
            title=job["title"],
            company=job.get("company"),
            location=job.get("location"),
            work_mode=job.get("work_mode"),
            employment_type=job.get("employment_type"),
            seniority=job.get("seniority"),
            description=job.get("description") or "",
            skills=list(job.get("skills") or []),
            must_have_skills=list(raw.get("must_have_skills") or job.get("skills") or []),
            adjacent_skills=list(raw.get("adjacent_skills") or []),
            ctc_inr_annual_min=job.get("ctc_inr_annual_min"),
            ctc_inr_annual_max=job.get("ctc_inr_annual_max"),
            notice_period_days=job.get("notice_period_days"),
            source_trusted=raw.get("source_trusted", True),
            company_type=raw.get("company_type"),
            posted_at=raw.get("posted_at"),
        )
    post = db.fetch_one("SELECT * FROM hiring_posts WHERE user_id = %s AND capture_id = %s", (user_id, capture_id))
    if post:
        return JobPosting(
            title=post.get("title") or "Hiring post",
            company=post.get("company"),
            location=cap.get("location"),
            description=post.get("excerpt") or "",
            skills=list(raw.get("skills") or []),
            must_have_skills=list(raw.get("must_have_skills") or []),
            adjacent_skills=list(raw.get("adjacent_skills") or []),
            source_trusted=raw.get("source_trusted", True),
            posted_at=raw.get("posted_at"),
        )
    return None


def _rematch_capture(user_id: str, capture_id: str, profile) -> bool:
    posting = _job_posting_from_capture(user_id, capture_id)
    if not posting:
        return False
    match = score_match_v2(posting, profile, evidence_ids=[capture_id])
    g_run = agents.start_run(user_id, "ganesha", "apply_hard_filters", posting.model_dump())
    a_run = agents.start_run(user_id, "arjuna", "score_match_v2", posting.model_dump())
    agents.finish_run(user_id, g_run, {"reasons": match.hard_filter_reasons})
    agents.finish_run(user_id, a_run, match.model_dump())

    job = db.fetch_one("SELECT id FROM jobs WHERE capture_id = %s AND user_id = %s", (capture_id, user_id))
    post = db.fetch_one("SELECT id FROM hiring_posts WHERE capture_id = %s AND user_id = %s", (capture_id, user_id))
    existing = db.fetch_one(
        "SELECT id FROM match_decisions WHERE user_id = %s AND capture_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id, capture_id),
    )
    breakdown = json.dumps([f.model_dump() for f in match.breakdown])
    if existing:
        db.execute(
            """
            UPDATE match_decisions SET
              passed_hard_filters = %s, hard_filter_reasons = %s, overall_score = %s, confidence = %s,
              breakdown = %s::jsonb, matched_skills = %s, missing_skills = %s, unknown_inputs = %s,
              reasons_to_apply = %s, risks = %s, freshness_hours = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                match.passed_hard_filters,
                match.hard_filter_reasons,
                match.overall_score,
                match.confidence,
                breakdown,
                match.matched_skills,
                match.missing_skills,
                match.unknown_inputs,
                match.reasons_to_apply,
                match.risks,
                match.freshness_hours,
                existing["id"],
                user_id,
            ),
        )
        decision_id = str(existing["id"])
    else:
        decision_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO match_decisions (
              id, user_id, capture_id, job_id, hiring_post_id, passed_hard_filters, hard_filter_reasons,
              overall_score, confidence, breakdown, matched_skills, missing_skills, unknown_inputs,
              reasons_to_apply, risks, freshness_hours, evidence_ids
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                decision_id,
                user_id,
                capture_id,
                str(job["id"]) if job else None,
                str(post["id"]) if post else None,
                match.passed_hard_filters,
                match.hard_filter_reasons,
                match.overall_score,
                match.confidence,
                breakdown,
                match.matched_skills,
                match.missing_skills,
                match.unknown_inputs,
                match.reasons_to_apply,
                match.risks,
                match.freshness_hours,
                [capture_id],
            ),
        )
    inbox = db.fetch_one("SELECT id, state FROM inbox_items WHERE user_id = %s AND capture_id = %s", (user_id, capture_id))
    if inbox:
        db.execute(
            "UPDATE inbox_items SET match_decision_id = %s, updated_at = now() WHERE id = %s AND user_id = %s",
            (decision_id, inbox["id"], user_id),
        )
    if match.passed_hard_filters and match.overall_score >= settings.strong_match_threshold:
        if not inbox:
            from jobhunt_api.services.inbox_transitions import transition_inbox

            inbox_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO inbox_items (id, user_id, capture_id, job_id, hiring_post_id, match_decision_id, state)
                VALUES (%s, %s, %s, %s, %s, %s, 'review_required')
                """,
                (
                    inbox_id,
                    user_id,
                    capture_id,
                    str(job["id"]) if job else None,
                    str(post["id"]) if post else None,
                    decision_id,
                ),
            )
        elif inbox["state"] in {"matched", "normalized"}:
            from jobhunt_api.services.inbox_transitions import transition_inbox

            transition_inbox(user_id, str(inbox["id"]), str(inbox["state"]), "review_required", "rematch", None)
    return True
