from fastapi import APIRouter, Depends

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import applications as app_svc
from jobhunt_api.services.connector_health import connector_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(user: dict = Depends(current_user)) -> dict:
    uid = user["user_id"]
    recs = db.fetch_all(
        """
        SELECT i.id, c.title, c.company, m.overall_score, i.state
        FROM inbox_items i
        JOIN source_captures c ON c.id = i.capture_id
        LEFT JOIN match_decisions m ON m.id = i.match_decision_id
        WHERE i.user_id = %s AND i.rejected = false
        ORDER BY m.overall_score DESC NULLS LAST
        LIMIT 8
        """,
        (uid,),
    )
    pending = db.fetch_one("SELECT count(*)::int AS n FROM approval_tasks WHERE user_id = %s AND status = 'pending'", (uid,))
    scans = db.fetch_all("SELECT id, status, last_error, created_at FROM scan_jobs WHERE user_id = %s ORDER BY created_at DESC LIMIT 5", (uid,))
    timeline = db.fetch_all("SELECT agent_name, status, created_at FROM agent_runs WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (uid,))
    connectors = connector_dashboard(uid)
    freshness = {
        c["connector_id"]: c.get("last_successful_sync") or c["implementation_status"] for c in connectors
    }
    return {
        "recommended": recs,
        "pending_approvals": pending["n"] if pending else 0,
        "scan_health": scans,
        "connector_health": connectors,
        "applications_by_stage": app_svc.counts_by_stage(uid),
        "upcoming_follow_ups": [],
        "interview_reminders": [],
        "source_freshness": freshness,
        "agent_timeline": timeline,
    }
