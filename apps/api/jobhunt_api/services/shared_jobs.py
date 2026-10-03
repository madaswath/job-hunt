"""Upsert normalized captures into the cross-tenant shared jobs index."""

from __future__ import annotations

import json
import uuid

from jobhunt_connectors.contract import RawCapture
from jobhunt_connectors.normalize import NormalizedCapture

from jobhunt_api import db


def upsert_shared_job(raw: RawCapture, normalized: NormalizedCapture) -> str | None:
    """Insert or refresh a shared catalogue row. Returns shared_jobs.id when written."""
    if raw.capture_kind not in {"job_listing", "hiring_post", "email_alert"}:
        return None
    apply_url = (raw.extracted_apply_urls or [None])[0]
    row = db.fetch_one(
        """
        INSERT INTO shared_jobs (
          id, source_connector, external_id, canonical_url, content_hash, title, company, location,
          work_mode, employment_type, seniority, description, excerpt, skills, must_have_skills,
          ctc_inr_annual_min, ctc_inr_annual_max, source_url, apply_url, extracted_emails,
          capture_kind, raw_payload, first_seen_at, last_seen_at
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now()
        )
        ON CONFLICT (content_hash) DO UPDATE SET
          last_seen_at = now(),
          title = EXCLUDED.title,
          company = EXCLUDED.company,
          location = EXCLUDED.location,
          work_mode = EXCLUDED.work_mode,
          apply_url = COALESCE(EXCLUDED.apply_url, shared_jobs.apply_url),
          extracted_emails = CASE
            WHEN cardinality(EXCLUDED.extracted_emails) > 0 THEN EXCLUDED.extracted_emails
            ELSE shared_jobs.extracted_emails
          END,
          raw_payload = EXCLUDED.raw_payload
        RETURNING id
        """,
        (
            str(uuid.uuid4()),
            raw.connector_id,
            raw.external_id,
            normalized.canonical_url,
            normalized.content_hash,
            raw.title or "Untitled",
            raw.company,
            raw.location,
            raw.work_mode,
            raw.employment_type,
            raw.seniority,
            raw.description,
            raw.excerpt,
            raw.skills or [],
            raw.must_have_skills or [],
            raw.ctc_inr_annual_min,
            raw.ctc_inr_annual_max,
            raw.source_url,
            apply_url,
            raw.extracted_emails or [],
            raw.capture_kind,
            json.dumps(raw.raw or raw.model_dump()),
        ),
    )
    return str(row["id"]) if row else None


def list_shared_jobs(limit: int = 50) -> list[dict]:
    return db.fetch_all(
        """
        SELECT id, source_connector, external_id, title, company, location, work_mode,
               source_url, apply_url, last_seen_at
        FROM shared_jobs
        ORDER BY last_seen_at DESC
        LIMIT %s
        """,
        (limit,),
    )
