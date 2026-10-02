from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from jobhunt_connectors.catalog import CONNECTOR_CATALOG
from pydantic import BaseModel, Field

from jobhunt_api.auth import current_user
from jobhunt_api.services import gmail_oauth, production_gates
from jobhunt_api.services import sources as source_svc
from jobhunt_api.services.connector_health import connector_dashboard

router = APIRouter(tags=["sources"])


class ConnectIn(BaseModel):
    labels: list[str] = Field(default_factory=list)
    refresh_token: str | None = None
    oauth_refresh_token: str | None = None


class BrowserCaptureIn(BaseModel):
    source_url: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    excerpt: str | None = None
    description: str | None = None
    author: str | None = None
    capture_kind: str | None = None
    extracted_apply_urls: list[str] = Field(default_factory=list)
    extracted_emails: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    work_mode: str | None = None
    capture_method: str = "browser_bookmarklet"


class IngestIn(BaseModel):
    labels: list[str] = Field(default_factory=list)
    fixture_path: str | None = None


@router.get("/sources")
def list_sources(user: dict = Depends(current_user)) -> dict:
    accounts = {a["connector_id"]: a for a in source_svc.list_accounts(user["user_id"])}
    items = []
    for conn in CONNECTOR_CATALOG.values():
        policy = conn.policy()
        acct = accounts.get(conn.id)
        health = conn.health()
        if conn.id == "gmail_alerts":
            health = {**health, "production_live": production_gates.gmail_production_live()}
        if acct:
            health = {
                **health,
                "account_status": acct["status"],
                "health_status": acct.get("health_status"),
                "last_ingest_at": acct.get("last_ingest_at"),
                "consent_at": acct.get("consent_at"),
                "revoked_at": acct.get("revoked_at"),
            }
        items.append(
            {
                "id": conn.id,
                "slug": conn.slug,
                "status": conn.status,
                "policy": policy.model_dump(),
                "capabilities": conn.capability_report().model_dump(),
                "health": health,
                "account": acct,
            }
        )
    return {"sources": items}


@router.get("/sources/accounts")
def list_accounts(user: dict = Depends(current_user)) -> dict:
    return {"accounts": source_svc.list_accounts(user["user_id"])}


@router.post("/sources/{connector_id}/connect")
def connect_source(connector_id: str, body: ConnectIn, user: dict = Depends(current_user)) -> dict:
    try:
        return source_svc.connect(user["user_id"], connector_id, body.model_dump())
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/sources/{connector_id}/revoke")
def revoke_source(connector_id: str, user: dict = Depends(current_user)) -> dict:
    return source_svc.revoke(user["user_id"], connector_id)


@router.post("/sources/{connector_id}/ingest")
def ingest_source(connector_id: str, body: IngestIn, user: dict = Depends(current_user)) -> dict:
    try:
        return source_svc.queue_ingest(user["user_id"], connector_id, body.model_dump(exclude_none=True))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/sources/browser-capture")
def browser_capture(body: BrowserCaptureIn, user: dict = Depends(current_user)) -> dict:
    uid = user["user_id"]
    acct = source_svc.list_accounts(uid)
    if not any(a["connector_id"] == "browser_capture" and a["status"] == "connected" for a in acct):
        source_svc.connect(uid, "browser_capture", {"labels": []})
    payload: dict[str, Any] = {"capture": body.model_dump()}
    try:
        return source_svc.queue_ingest(uid, "browser_capture", payload)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/sources/health")
def sources_health(user: dict = Depends(current_user)) -> dict:
    return {"connectors": connector_dashboard(user["user_id"])}


@router.post("/sources/gmail_alerts/oauth/start")
def gmail_oauth_start(body: ConnectIn, user: dict = Depends(current_user)) -> dict:
    production_gates.assert_gmail_oauth()
    try:
        return gmail_oauth.start_oauth(user["user_id"], body.labels or [])
    except gmail_oauth.GmailOAuthError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/sources/gmail_alerts/oauth/callback")
def gmail_oauth_callback(state: str, code: str) -> dict:
    try:
        return gmail_oauth.complete_oauth(state, code)
    except gmail_oauth.GmailOAuthError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/sources/{connector_id}/policy")
def source_policy(connector_id: str, user: dict = Depends(current_user)) -> dict:
    conn = CONNECTOR_CATALOG.get(connector_id)
    if not conn:
        raise HTTPException(404, "unknown connector")
    row = source_svc.list_accounts(user["user_id"])
    stored = next((r for r in row if r["connector_id"] == connector_id), None)
    return {"connector_id": connector_id, "policy": conn.policy().model_dump(), "stored": stored}
