import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import audit
from jobhunt_api.services import sources as source_svc

router = APIRouter(tags=["discovery"])


class ScanIn(BaseModel):
    connector_id: str = "public_ats_fixture"
    titles: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    work_mode: str | None = None
    saved_search_name: str | None = None


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
                    if any(term in lowered for term in ("cookie", "session", "password", "authorization", "bearer", "email_draft", "generated_email")):
                        raise ValueError(f"{path}{key} is not accepted in a candidate import")
                    walk(child, f"{path}{key}.")
            elif isinstance(value, list):
                for child in value:
                    walk(child, path)

        walk(self.model_dump())
        if not self.jobs and not self.posts:
            raise ValueError("import must include at least one job or hiring post")
        return self


@router.get("/discovery/saved-searches")
def list_saved(user: dict = Depends(current_user)) -> dict:
    rows = db.fetch_all("SELECT id, name, query, created_at FROM saved_searches WHERE user_id = %s ORDER BY created_at DESC", (user["user_id"],))
    return {"saved_searches": rows}


@router.post("/discovery/scans")
def queue_scan(body: ScanIn, user: dict = Depends(current_user)) -> dict:
    if body.connector_id == "gmail_alerts":
        source_svc.require_connected(user["user_id"], "gmail_alerts")
        source_svc.assert_ingest_rate(user["user_id"], "gmail_alerts")
    if body.saved_search_name:
        db.execute(
            "INSERT INTO saved_searches (user_id, name, query) VALUES (%s, %s, %s::jsonb)",
            (user["user_id"], body.saved_search_name, json.dumps(body.model_dump())),
        )
    key = str(uuid.uuid4())
    row = db.fetch_one(
        """
        INSERT INTO scan_jobs (user_id, connector_id, payload, idempotency_key)
        VALUES (%s, %s, %s::jsonb, %s)
        RETURNING id, status
        """,
        (user["user_id"], body.connector_id, json.dumps(body.model_dump()), key),
    )
    audit.record(user["user_id"], "scan_queued", "scan_job", str(row["id"]), {"connector": body.connector_id})
    return {"scan_job_id": str(row["id"]), "status": row["status"]}


@router.post("/discovery/candidate-imports")
def queue_candidate_import(body: CandidateImportIn, user: dict = Depends(current_user)) -> dict:
    """Queue a user-uploaded export; this endpoint never fetches a source site."""
    export = body.model_dump()
    key = str(uuid.uuid4())
    row = db.fetch_one(
        """
        INSERT INTO scan_jobs (user_id, connector_id, payload, idempotency_key)
        VALUES (%s, 'candidate_import', %s::jsonb, %s)
        RETURNING id, status
        """,
        (user["user_id"], json.dumps({"export": export}), key),
    )
    audit.record(
        user["user_id"],
        "candidate_import_queued",
        "scan_job",
        str(row["id"]),
        {
            "jobs": len(body.jobs),
            "posts": len(body.posts),
            "engine": body.metadata.get("engine"),
            "titles": body.titles,
            "cities": body.cities,
        },
    )
    return {"scan_job_id": str(row["id"]), "status": row["status"], "jobs": len(body.jobs), "posts": len(body.posts)}
