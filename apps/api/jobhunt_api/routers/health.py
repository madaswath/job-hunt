from fastapi import APIRouter

from jobhunt_api import db
from jobhunt_api.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api"}


@router.get("/ready")
def ready() -> dict:
    db.fetch_one("SELECT 1 AS ok")
    return {"status": "ready", "database": True, "us_market": settings.feature_us_market}


@router.get("/worker-metrics")
def worker_metrics() -> dict:
    backlog = db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE status IN ('queued','running')")
    failed = db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE status IN ('failed','dead_letter')")
    retries = db.fetch_one("SELECT coalesce(sum(attempts),0)::int AS n FROM scan_jobs")
    return {
        "backlog": backlog["n"] if backlog else 0,
        "failures": failed["n"] if failed else 0,
        "retry_count": retries["n"] if retries else 0,
        "source_health": {"public_ats_fixture": "live"},
    }
