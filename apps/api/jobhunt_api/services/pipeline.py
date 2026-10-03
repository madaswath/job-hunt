import json
import time
import uuid

from jobhunt_connectors.catalog import get_connector
from jobhunt_connectors.contract import RawCapture
from jobhunt_domain.matching import score_match_v2
from jobhunt_domain.schemas import CandidateProfile, JobPosting
from jobhunt_policy.rules import assert_connector_operation

from jobhunt_api import db
from jobhunt_api.services import agents
from jobhunt_api.services import sources as source_svc
from jobhunt_api.services.inbox_transitions import transition_inbox
from jobhunt_api.services.profile_loader import load_candidate_profile
from jobhunt_api.services.rematch import rematch_user_captures
from jobhunt_api.services.shared_jobs import upsert_shared_job
from jobhunt_api.settings import settings


def process_scan_job(job_row: dict) -> dict:
    user_id = job_row["user_id"]
    connector_id = job_row["connector_id"]
    payload = job_row["payload"] if isinstance(job_row["payload"], dict) else json.loads(job_row["payload"])
    if connector_id == "rematch" or payload.get("rematch"):
        return rematch_user_captures(user_id)
    assert_connector_operation(connector_id, "ingest")
    connector = get_connector(connector_id)
    profile = load_candidate_profile(user_id)
    started = time.time()
    narada_run = agents.start_run(user_id, "narada", "connector_ingest", payload)
    ctx: dict = {"user_id": user_id}
    ingest_payload = dict(payload)
    if connector_id == "gmail_alerts" and ingest_payload.get("use_gmail_api"):
        from jobhunt_api.services.gmail_tokens import TokenRefreshFailed, get_access_token
        from jobhunt_api.services.observability import raise_alert

        try:
            ctx["access_token"] = get_access_token(user_id)
        except TokenRefreshFailed as exc:
            raise_alert("token_expiry", {"user_id": user_id, "error": str(exc)}, severity="critical")
            raise
    try:
        raws = connector.ingest(ctx, ingest_payload)
    except Exception as exc:
        from jobhunt_connectors.gmail_failures import GmailIngestError

        from jobhunt_api.services.observability import raise_alert
        from jobhunt_api.services.worker_observability import record_scan_failure

        if isinstance(exc, GmailIngestError):
            record_scan_failure(user_id, connector_id, f"{exc.kind.value}: {exc}")
            raise_alert(
                "ingestion_failed",
                {"user_id": user_id, "connector": connector_id, "kind": exc.kind.value},
                severity="warning",
            )
        raise
    created = 0
    for raw in raws:
        created += int(_ingest_one(user_id, connector, raw, profile))
    agents.finish_run(user_id, narada_run, {"ingested": len(raws), "created": created}, started=started)
    if connector_id in {"gmail_alerts", "browser_capture", "candidate_import", "public_ats_fixture", "linkedin"}:
        source_svc.mark_ingest_complete(user_id, connector_id, {"ingested": len(raws), "created": created})
    _enqueue_outbox(
        user_id,
        "notification",
        f"scan-{job_row['id']}",
        {"title": "Scan complete", "body": f"{created} new matches processed"},
    )
    return {"created": created, "seen": len(raws)}


def _ingest_one(user_id: str, connector, raw: RawCapture, profile: CandidateProfile) -> bool:
    with db.unit_of_work():
        return _ingest_one_tx(user_id, connector, raw, profile)


def _ingest_one_tx(user_id: str, connector, raw: RawCapture, profile: CandidateProfile) -> bool:
    normalized = connector.normalize(raw)
    try:
        upsert_shared_job(raw, normalized, search_keyword=(raw.raw or {}).get("keyword") if isinstance(raw.raw, dict) else None, posted_at=raw.posted_at)
    except Exception:
        # Shared index is additive; per-user ingest must not fail if migration 006/007 is absent in older DBs.
        pass
    existing = db.fetch_one(
        """
        SELECT id FROM source_captures
        WHERE user_id = %s AND (
          content_hash = %s
          OR (connector_id = %s AND external_id IS NOT NULL AND external_id = %s)
          OR (canonical_url IS NOT NULL AND canonical_url = %s)
        )
        LIMIT 1
        """,
        (user_id, normalized.content_hash, raw.connector_id, raw.external_id, normalized.canonical_url),
    )
    if existing:
        return False
    capture_id = str(uuid.uuid4())
    idem = f"{raw.connector_id}:{raw.external_id or normalized.content_hash}"
    db.execute(
        """
        INSERT INTO source_captures (
          id, user_id, connector_id, capture_kind, external_id, source_url, canonical_url,
          company, title, location, excerpt, raw_payload, content_hash, author,
          extracted_emails, extracted_apply_urls, capture_method, idempotency_key
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            capture_id,
            user_id,
            raw.connector_id,
            raw.capture_kind,
            raw.external_id,
            raw.source_url,
            normalized.canonical_url,
            raw.company,
            raw.title,
            raw.location,
            raw.excerpt,
            json.dumps(raw.raw or raw.model_dump()),
            normalized.content_hash,
            raw.author,
            raw.extracted_emails,
            raw.extracted_apply_urls,
            raw.capture_method,
            idem,
        ),
    )
    job_id = None
    post_id = None
    if normalized.kind == "hiring_post":
        post_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO hiring_posts (id, user_id, capture_id, title, company, author, excerpt, source_url, extracted_emails, extracted_apply_urls)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                post_id,
                user_id,
                capture_id,
                raw.title,
                raw.company,
                raw.author,
                raw.excerpt,
                raw.source_url,
                raw.extracted_emails,
                raw.extracted_apply_urls,
            ),
        )
    else:
        job_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO jobs (
              id, user_id, capture_id, title, company, location, work_mode, employment_type, seniority,
              description, skills, ctc_inr_annual_min, ctc_inr_annual_max, notice_period_days, source_url, apply_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job_id,
                user_id,
                capture_id,
                raw.title or "Untitled",
                raw.company,
                raw.location,
                raw.work_mode,
                raw.employment_type,
                raw.seniority,
                raw.description,
                raw.skills,
                raw.ctc_inr_annual_min,
                raw.ctc_inr_annual_max,
                raw.notice_period_days,
                raw.source_url,
                (raw.extracted_apply_urls or [None])[0],
            ),
        )

    posting = JobPosting(
        title=raw.title or "",
        company=raw.company,
        location=raw.location,
        work_mode=raw.work_mode,
        employment_type=raw.employment_type,
        seniority=raw.seniority,
        description=raw.description,
        skills=raw.skills,
        must_have_skills=raw.must_have_skills,
        adjacent_skills=raw.adjacent_skills,
        ctc_inr_annual_min=raw.ctc_inr_annual_min,
        ctc_inr_annual_max=raw.ctc_inr_annual_max,
        notice_period_days=raw.notice_period_days,
        source_trusted=raw.source_trusted,
        company_type=raw.company_type,
        posted_at=raw.posted_at,
    )
    g_run = agents.start_run(user_id, "ganesha", "apply_hard_filters", posting.model_dump())
    a_run = agents.start_run(user_id, "arjuna", "score_match_v2", posting.model_dump())
    match = score_match_v2(posting, profile, evidence_ids=[capture_id])
    agents.finish_run(user_id, g_run, {"reasons": match.hard_filter_reasons})
    agents.finish_run(user_id, a_run, match.model_dump())
    decision_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO match_decisions (
          id, user_id, capture_id, job_id, hiring_post_id, passed_hard_filters, hard_filter_reasons,
          overall_score, confidence, breakdown, matched_skills, missing_skills, unknown_inputs,
          reasons_to_apply, risks, freshness_hours, evidence_ids
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            decision_id,
            user_id,
            capture_id,
            job_id,
            post_id,
            match.passed_hard_filters,
            match.hard_filter_reasons,
            match.overall_score,
            match.confidence,
            json.dumps([f.model_dump() for f in match.breakdown]),
            match.matched_skills,
            match.missing_skills,
            match.unknown_inputs,
            match.reasons_to_apply,
            match.risks,
            match.freshness_hours,
            [capture_id],
        ),
    )
    if not match.passed_hard_filters or match.overall_score < settings.strong_match_threshold:
        return True
    inbox_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO inbox_items (id, user_id, capture_id, job_id, hiring_post_id, match_decision_id, state)
        VALUES (%s, %s, %s, %s, %s, %s, 'captured')
        """,
        (inbox_id, user_id, capture_id, job_id, post_id, decision_id),
    )
    transition_inbox(user_id, inbox_id, "captured", "normalized", "narada", None)
    transition_inbox(user_id, inbox_id, "normalized", "matched", "arjuna", None)
    transition_inbox(user_id, inbox_id, "matched", "review_required", "strong_match", None)
    return True


def _enqueue_outbox(user_id: str, event_type: str, idempotency_key: str, payload: dict) -> None:
    db.execute(
        """
        INSERT INTO outbox_events (user_id, event_type, payload, idempotency_key)
        VALUES (%s, %s, %s::jsonb, %s)
        ON CONFLICT (idempotency_key) DO NOTHING
        """,
        (user_id, event_type, json.dumps(payload), idempotency_key),
    )


def deliver_outbox(event: dict) -> None:
    payload = event["payload"] if isinstance(event["payload"], dict) else json.loads(event["payload"])
    if event["event_type"] != "notification":
        raise PermissionError("phase 1 outbox only delivers notifications")
    existing = db.fetch_one(
        "SELECT id FROM notifications WHERE user_id = %s AND title = %s AND body = %s LIMIT 1",
        (event["user_id"], payload.get("title"), payload.get("body")),
    )
    if not existing:
        db.execute(
            "INSERT INTO notifications (user_id, title, body) VALUES (%s, %s, %s)",
            (event["user_id"], payload.get("title"), payload.get("body")),
        )
    db.execute(
        "UPDATE outbox_events SET status = 'delivered', delivered_at = now() WHERE id = %s",
        (event["id"],),
    )


def claim_scan_jobs(limit: int = 5, lease_seconds: int = 60) -> list[dict]:
    with db.unit_of_work():
        db.execute(
            """
            UPDATE scan_jobs SET status = 'queued', leased_until = NULL
            WHERE status = 'running' AND leased_until IS NOT NULL AND leased_until < now()
            """
        )
        return db.fetch_all(
            """
            UPDATE scan_jobs
            SET status = 'running',
                attempts = attempts + 1,
                leased_until = now() + (%s || ' seconds')::interval,
                updated_at = now()
            WHERE id IN (
              SELECT id FROM scan_jobs
              WHERE status IN ('queued', 'running')
                AND (leased_until IS NULL OR leased_until < now())
                AND attempts < max_attempts
              ORDER BY created_at
              FOR UPDATE SKIP LOCKED
              LIMIT %s
            )
            RETURNING *
            """,
            (str(lease_seconds), limit),
        )


def claim_outbox(limit: int = 10, lease_seconds: int = 30) -> list[dict]:
    return db.fetch_all(
        """
        UPDATE outbox_events
        SET status = 'running',
            attempts = attempts + 1,
            leased_until = now() + (%s || ' seconds')::interval
        WHERE id IN (
          SELECT id FROM outbox_events
          WHERE status = 'pending' OR (status = 'running' AND leased_until < now())
          ORDER BY created_at
          FOR UPDATE SKIP LOCKED
          LIMIT %s
        )
        RETURNING *
        """,
        (str(lease_seconds), limit),
    )


def complete_scan(job_id: str, ok: bool, error: str | None = None) -> None:
    if ok:
        db.execute(
            "UPDATE scan_jobs SET status = 'completed', last_error = NULL, updated_at = now() WHERE id = %s",
            (job_id,),
        )
        return
    row = db.fetch_one("SELECT attempts, max_attempts FROM scan_jobs WHERE id = %s", (job_id,))
    status = "dead_letter" if row and row["attempts"] >= row["max_attempts"] else "queued"
    backoff = min(300, 2 ** (row["attempts"] if row else 1))
    db.execute(
        """
        UPDATE scan_jobs SET status = %s, last_error = %s, leased_until = now() + (%s || ' seconds')::interval, updated_at = now()
        WHERE id = %s
        """,
        (status, error, str(backoff), job_id),
    )
