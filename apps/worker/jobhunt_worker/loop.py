import os
import threading
import time

import uvicorn
from fastapi import FastAPI
from jobhunt_api import db
from jobhunt_api.redact import redact
from jobhunt_api.services.connector_health import worker_connector_summary
from jobhunt_api.services.observability import alert_counts_24h, recent_alerts
from jobhunt_api.services.pipeline import claim_outbox, claim_scan_jobs, complete_scan, deliver_outbox, process_scan_job
from jobhunt_api.services.worker_observability import maintenance_tick, record_scan_failure

metrics_app = FastAPI(title="Job-hunt worker")


@metrics_app.get("/health")
def health() -> dict:
    backlog = db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE status IN ('queued','running')")
    failed = db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE status IN ('failed','dead_letter')")
    retries = db.fetch_one("SELECT coalesce(sum(attempts),0)::int AS n FROM scan_jobs")
    external = os.environ.get("FEATURE_EXTERNAL_GMAIL", "false").lower() in {"1", "true", "yes", "on"}
    return {
        "status": "ok",
        "service": "worker",
        "feature_external_gmail": external,
        "backlog": backlog["n"] if backlog else 0,
        "failures": failed["n"] if failed else 0,
        "retry_count": retries["n"] if retries else 0,
        "alerts": worker_connector_summary(),
    }


@metrics_app.get("/metrics")
def metrics() -> dict:
    return {
        "worker": worker_connector_summary(),
        "alerts_24h": alert_counts_24h(),
        "recent_alerts": recent_alerts(20),
    }


@metrics_app.get("/ready")
def ready() -> dict:
    db.fetch_one("SELECT 1 AS ok")
    return {"status": "ready"}


def run_once() -> dict:
    processed = 0
    for job in claim_scan_jobs():
        try:
            process_scan_job(job)
            complete_scan(str(job["id"]), True)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            print(redact(f"scan failed {job['id']} {exc}"))
            record_scan_failure(job["user_id"], job["connector_id"], str(exc))
            complete_scan(str(job["id"]), False, str(exc))
    maintenance_tick()
    for event in claim_outbox():
        try:
            deliver_outbox(event)
        except Exception as exc:  # noqa: BLE001
            print(redact(f"outbox failed {event['id']} {exc}"))
            db.execute(
                "UPDATE outbox_events SET status = 'pending' WHERE id = %s AND attempts < 8",
                (event["id"],),
            )
    return {"processed": processed}


def loop() -> None:
    interval = float(os.environ.get("WORKER_POLL_SECONDS", "2"))
    while True:
        run_once()
        time.sleep(interval)


def main() -> None:
    threading.Thread(target=loop, daemon=True).start()
    uvicorn.run(metrics_app, host="0.0.0.0", port=int(os.environ.get("WORKER_PORT", "8001")))
