import json
import uuid

from fastapi import APIRouter, Depends
from jobhunt_domain.india import BETA_DS_AI_TITLES
from pydantic import BaseModel, Field, model_validator

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import audit
from jobhunt_api.services import sources as source_svc

router = APIRouter(tags=["discovery"])

DEMO1_CONNECTORS = ("public_ats_fixture", "linkedin", "gmail_alerts")


class ScanIn(BaseModel):
    connector_id: str = "public_ats_fixture"
    titles: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    work_mode: str | None = None
    saved_search_name: str | None = None


class Demo1RefreshIn(BaseModel):
    titles: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    work_mode: str | None = "hybrid"
    enable_autopilot: bool = True
    interval_hours: int = Field(default=24, ge=6, le=168)


class CandidateImportIn(BaseModel):
    """Safe subset of the browserless export produced on a candidate device."""

    metadata: dict = Field(default_factory=dict)
    jobs: list[dict] = Field(default_factory=list, max_length=100)
    posts: list[dict] = Field(default_factory=list, max_length=100)
    titles: list[str] = Field(default_factory=list, max_length=10)
    cities: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def reject_sensitive_or_generated_fields(self):
        def walk(value, path=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    lowered = key.lower()
                    if any(
                        term in lowered
                        for term in (
                            "cookie",
                            "session",
                            "password",
                            "authorization",
                            "bearer",
                            "email_draft",
                            "generated_email",
                        )
                    ):
                        raise ValueError(f"{path}{key} is not accepted in a candidate import")
                    walk(child, f"{path}{key}.")
            elif isinstance(value, list):
                for child in value:
                    walk(child, path)

        walk(self.model_dump())
        if not self.jobs and not self.posts:
            raise ValueError("import must include at least one job or hiring post")
        return self


def _queue_scan(user_id: str, connector_id: str, payload: dict) -> dict:
    key = str(uuid.uuid4())
    row = db.fetch_one(
        """
        INSERT INTO scan_jobs (user_id, connector_id, payload, idempotency_key)
        VALUES (%s, %s, %s::jsonb, %s)
        RETURNING id, status
        """,
        (user_id, connector_id, json.dumps(payload), key),
    )
    audit.record(user_id, "scan_queued", "scan_job", str(row["id"]), {"connector": connector_id})
    return {"scan_job_id": str(row["id"]), "status": row["status"], "connector_id": connector_id}


@router.get("/discovery/saved-searches")
def list_saved(user: dict = Depends(current_user)) -> dict:
    rows = db.fetch_all(
        "SELECT id, name, query, created_at FROM saved_searches WHERE user_id = %s ORDER BY created_at DESC",
        (user["user_id"],),
    )
    return {"saved_searches": rows}


@router.post("/discovery/scans")
def queue_scan(body: ScanIn, user: dict = Depends(current_user)) -> dict:
    if body.connector_id == "gmail_alerts":
        source_svc.require_connected(user["user_id"], "gmail_alerts")
        source_svc.assert_ingest_rate(user["user_id"], "gmail_alerts")
    if body.connector_id == "linkedin":
        source_svc.require_connected(user["user_id"], "linkedin")
        source_svc.assert_ingest_rate(user["user_id"], "linkedin")
    if body.saved_search_name:
        db.execute(
            "INSERT INTO saved_searches (user_id, name, query) VALUES (%s, %s, %s::jsonb)",
            (user["user_id"], body.saved_search_name, json.dumps(body.model_dump())),
        )
    return _queue_scan(user["user_id"], body.connector_id, body.model_dump())


@router.post("/discovery/demo1-refresh")
def demo1_refresh(body: Demo1RefreshIn, user: dict = Depends(current_user)) -> dict:
    """Queue Gmail + LinkedIn + ATS fixture ingest for Demo 1 autopilot."""
    # Prefer broad ingest; Match v2 + profile do ruthless ranking into inbox.
    # Only apply title substrings when the user explicitly narrowed the refresh.
    ingest_titles = body.titles
    schedule_titles = body.titles or list(BETA_DS_AI_TITLES)
    cities = body.cities or ["Bengaluru", "Hyderabad", "Pune", "Chennai", "Mumbai", "Gurugram", "Noida", "remote"]
    payload_base = {
        "titles": ingest_titles,
        "cities": cities,
        "work_mode": body.work_mode,
        "saved_search_name": "demo1-refresh",
    }

    # Fixture consent for Demo 1 sources (Gmail API still gated separately).
    source_svc.connect(user["user_id"], "gmail_alerts", {"labels": ["JobAlerts", "Jobs"]})
    source_svc.connect(user["user_id"], "linkedin", {})

    jobs = []
    for connector_id in DEMO1_CONNECTORS:
        source_svc.assert_ingest_rate(user["user_id"], connector_id)
        payload = {**payload_base, "connector_id": connector_id}
        if connector_id == "gmail_alerts":
            payload["use_gmail_api"] = False
        jobs.append(_queue_scan(user["user_id"], connector_id, payload))

    if body.enable_autopilot:
        db.execute(
            """
            INSERT INTO autopilot_schedules (
              user_id, enabled, interval_hours, titles, cities, work_mode, last_run_at, next_run_at
            )
            VALUES (%s, true, %s, %s, %s, %s, now(), now() + (%s || ' hours')::interval)
            ON CONFLICT (user_id) DO UPDATE SET
              enabled = true,
              interval_hours = EXCLUDED.interval_hours,
              titles = EXCLUDED.titles,
              cities = EXCLUDED.cities,
              work_mode = EXCLUDED.work_mode,
              last_run_at = now(),
              next_run_at = now() + (EXCLUDED.interval_hours || ' hours')::interval,
              updated_at = now()
            """,
            (
                user["user_id"],
                body.interval_hours,
                schedule_titles,
                cities,
                body.work_mode,
                str(body.interval_hours),
            ),
        )

    audit.record(
        user["user_id"],
        "demo1_refresh_queued",
        "discovery",
        None,
        {"connectors": list(DEMO1_CONNECTORS), "titles": schedule_titles, "cities": cities},
    )
    return {
        "status": "queued",
        "scans": jobs,
        "autopilot_enabled": body.enable_autopilot,
        "hint": "Start the worker, then open Review Inbox for ranked matches.",
    }


@router.post("/discovery/candidate-imports")
def queue_candidate_import(body: CandidateImportIn, user: dict = Depends(current_user)) -> dict:
    """Queue a user-uploaded export; this endpoint never fetches a source site."""
    export = body.model_dump()
    result = _queue_scan(user["user_id"], "candidate_import", {"export": export})
    audit.record(
        user["user_id"],
        "candidate_import_queued",
        "scan_job",
        result["scan_job_id"],
        {
            "jobs": len(body.jobs),
            "posts": len(body.posts),
            "engine": body.metadata.get("engine"),
            "titles": body.titles,
            "cities": body.cities,
        },
    )
    return {
        "scan_job_id": result["scan_job_id"],
        "status": result["status"],
        "jobs": len(body.jobs),
        "posts": len(body.posts),
    }
