"""Load LinkedIn scraper exports into shared_jobs master index and match users."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from jobhunt_connectors.catalog import get_connector
from jobhunt_connectors.contract import RawCapture
from jobhunt_connectors.normalize import normalize_capture
from jobhunt_domain.matching import score_match_v2
from jobhunt_domain.schemas import JobPosting

from jobhunt_api import db
from jobhunt_api.services import audit
from jobhunt_api.services.inbox_transitions import transition_inbox
from jobhunt_api.services.profile_loader import load_candidate_profile
from jobhunt_api.services.shared_jobs import upsert_shared_job
from jobhunt_api.settings import settings

DEFAULT_EXPORT_DIR = Path(__file__).resolve().parents[3] / "data" / "linkedin-exports"


def _export_root(export_dir: str | None = None) -> Path:
    return Path(export_dir or os.getenv("LINKEDIN_EXPORT_DIR") or DEFAULT_EXPORT_DIR)


def ingest_linkedin_master(
    *,
    user_id: str | None = None,
    export_dir: str | None = None,
    keywords: list[str] | None = None,
    skills: list[str] | None = None,
    preferences: list[str] | None = None,
    jobs_per_keyword: int = 100,
    posts_limit: int = 15,
    match_user: bool = True,
) -> dict:
    """Upsert capped scraper exports into shared_jobs; optionally rank into the caller's inbox."""
    posts_limit = max(10, min(int(posts_limit or 15), 15))
    jobs_per_keyword = max(1, min(int(jobs_per_keyword), 200))
    root = _export_root(export_dir)
    connector = get_connector("linkedin")
    query = {
        "use_export_dir": True,
        "export_dir": str(root),
        "keywords": keywords or [],
        "skills": skills or [],
        "preferences": preferences or [],
        "jobs_per_keyword": jobs_per_keyword,
        "posts_limit": posts_limit,
    }
    # If export dir missing, fall back to fixture so local demo still works.
    if not root.exists():
        query = {
            "fixture_path": str(
                Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "linkedin" / "postings.json"
            ),
            "jobs_per_keyword": jobs_per_keyword,
            "posts_limit": posts_limit,
        }

    raws: list[RawCapture] = connector.ingest({"user_id": user_id}, query)
    jobs_upserted = 0
    posts_upserted = 0
    by_keyword: dict[str, int] = {}
    shared_ids: list[str] = []

    for raw in raws:
        normalized = connector.normalize(raw)
        keyword = None
        if isinstance(raw.raw, dict):
            keyword = raw.raw.get("keyword")
        shared_id = upsert_shared_job(raw, normalized, search_keyword=keyword, posted_at=raw.posted_at)
        if shared_id:
            shared_ids.append(shared_id)
            key = str(keyword or "general")
            by_keyword[key] = by_keyword.get(key, 0) + 1
            if raw.capture_kind == "hiring_post":
                posts_upserted += 1
            else:
                jobs_upserted += 1

    run_id = str(uuid.uuid4())
    summary = {
        "export_dir": str(root),
        "by_keyword": by_keyword,
        "shared_ids_sample": shared_ids[:20],
        "raw_count": len(raws),
    }
    try:
        db.execute(
            """
            INSERT INTO linkedin_master_ingest_runs (
              id, user_id, export_dir, keywords, jobs_upserted, posts_upserted,
              jobs_per_keyword, posts_limit, status, summary
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'completed', %s::jsonb)
            """,
            (
                run_id,
                user_id,
                str(root),
                keywords or list(by_keyword.keys()),
                jobs_upserted,
                posts_upserted,
                jobs_per_keyword,
                posts_limit,
                json.dumps(summary),
            ),
        )
    except Exception:
        # Migration 007 may not be applied yet in older envs.
        pass

    if user_id:
        audit.record(
            user_id,
            "linkedin_master_ingested",
            "shared_jobs",
            run_id,
            {"jobs": jobs_upserted, "posts": posts_upserted, "keywords": by_keyword},
        )

    matched = 0
    if match_user and user_id:
        matched = match_user_from_shared(user_id, limit=80)

    return {
        "run_id": run_id,
        "export_dir": str(root),
        "jobs_upserted": jobs_upserted,
        "posts_upserted": posts_upserted,
        "by_keyword": by_keyword,
        "inbox_matches_created": matched,
    }


def match_user_from_shared(user_id: str, *, limit: int = 80) -> int:
    """Score recent shared_jobs against the user profile and open inbox items for strong matches."""
    profile = load_candidate_profile(user_id)
    rows = db.fetch_all(
        """
        SELECT *
        FROM shared_jobs
        ORDER BY COALESCE(posted_at, last_seen_at) DESC
        LIMIT %s
        """,
        (limit,),
    )
    created = 0
    for row in rows:
        created += int(_materialize_shared_row(user_id, row, profile))
    return created


def _materialize_shared_row(user_id: str, row: dict, profile) -> bool:
    content_hash = row.get("content_hash")
    existing = db.fetch_one(
        """
        SELECT id FROM source_captures
        WHERE user_id = %s AND (content_hash = %s OR (connector_id = %s AND external_id IS NOT NULL AND external_id = %s))
        LIMIT 1
        """,
        (user_id, content_hash, row.get("source_connector") or "linkedin", row.get("external_id")),
    )
    if existing:
        return False

    posting = JobPosting(
        title=row.get("title") or "",
        company=row.get("company"),
        location=row.get("location"),
        work_mode=row.get("work_mode"),
        employment_type=row.get("employment_type"),
        seniority=row.get("seniority"),
        description=row.get("description"),
        skills=row.get("skills") or [],
        must_have_skills=row.get("must_have_skills") or [],
        ctc_inr_annual_min=row.get("ctc_inr_annual_min"),
        ctc_inr_annual_max=row.get("ctc_inr_annual_max"),
        source_trusted=False,
        posted_at=row.get("posted_at"),
        company_type=None,
    )
    match = score_match_v2(posting, profile, evidence_ids=[str(row.get("id"))])
    if not match.passed_hard_filters or match.overall_score < settings.strong_match_threshold:
        return False

    capture_id = str(uuid.uuid4())
    external_id = row.get("external_id")
    idem = f"shared:{row.get('source_connector')}:{external_id or content_hash}"
    with db.unit_of_work():
        db.execute(
            """
            INSERT INTO source_captures (
              id, user_id, connector_id, capture_kind, external_id, source_url, canonical_url,
              company, title, location, excerpt, raw_payload, content_hash, author,
              extracted_emails, extracted_apply_urls, capture_method, idempotency_key
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (user_id, idempotency_key) DO NOTHING
            """,
            (
                capture_id,
                user_id,
                row.get("source_connector") or "linkedin",
                row.get("capture_kind") or "job_listing",
                external_id,
                row.get("source_url"),
                row.get("canonical_url"),
                row.get("company"),
                row.get("title"),
                row.get("location"),
                row.get("excerpt"),
                json.dumps(row.get("raw_payload") or {}),
                content_hash,
                None,
                row.get("extracted_emails") or [],
                [row["apply_url"]] if row.get("apply_url") else [],
                "shared_master_match",
                idem,
            ),
        )
        # If conflict, skip
        wrote = db.fetch_one("SELECT id FROM source_captures WHERE id = %s", (capture_id,))
        if not wrote:
            return False

        job_id = None
        post_id = None
        if row.get("capture_kind") == "hiring_post":
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
                    row.get("title"),
                    row.get("company"),
                    None,
                    row.get("excerpt"),
                    row.get("source_url") or "",
                    row.get("extracted_emails") or [],
                    [row["apply_url"]] if row.get("apply_url") else [],
                ),
            )
        else:
            job_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO jobs (
                  id, user_id, capture_id, title, company, location, work_mode, employment_type, seniority,
                  description, skills, ctc_inr_annual_min, ctc_inr_annual_max, source_url, apply_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job_id,
                    user_id,
                    capture_id,
                    row.get("title") or "Untitled",
                    row.get("company"),
                    row.get("location"),
                    row.get("work_mode"),
                    row.get("employment_type"),
                    row.get("seniority"),
                    row.get("description"),
                    row.get("skills") or [],
                    row.get("ctc_inr_annual_min"),
                    row.get("ctc_inr_annual_max"),
                    row.get("source_url"),
                    row.get("apply_url"),
                ),
            )

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
                [str(row.get("id")), capture_id],
            ),
        )
        inbox_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO inbox_items (id, user_id, capture_id, job_id, hiring_post_id, match_decision_id, state)
            VALUES (%s, %s, %s, %s, %s, %s, 'captured')
            """,
            (inbox_id, user_id, capture_id, job_id, post_id, decision_id),
        )
        transition_inbox(user_id, inbox_id, "captured", "normalized", "shared_master", None)
        transition_inbox(user_id, inbox_id, "normalized", "matched", "arjuna", None)
        transition_inbox(user_id, inbox_id, "matched", "review_required", "strong_match", None)
    return True
