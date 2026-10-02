import hashlib
import json
import time
import uuid

from jobhunt_agents.permissions import assert_agent_permission

from jobhunt_api import db
from jobhunt_api.services import audit


def start_run(user_id: str, agent_name: str, tool: str, payload: dict, context: dict | None = None) -> str:
    assert_agent_permission(agent_name, tool, context)
    run_id = str(uuid.uuid4())
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    db.execute(
        """
        INSERT INTO agent_runs (run_id, user_id, agent_name, status, input_hash, model_version, allowed_tools)
        VALUES (%s, %s, %s, 'running', %s, 'deterministic-v1', %s)
        """,
        (run_id, user_id, agent_name, digest, [tool]),
    )
    return run_id


def finish_run(user_id: str, run_id: str, artifact: dict, status: str = "completed", error: str | None = None, started: float | None = None) -> None:
    duration = int((time.time() - started) * 1000) if started else None
    db.execute(
        "UPDATE agent_runs SET status = %s, error = %s, duration_ms = %s WHERE run_id = %s AND user_id = %s",
        (status, error, duration, run_id, user_id),
    )
    db.execute(
        "INSERT INTO agent_artifacts (user_id, run_id, kind, payload) VALUES (%s, %s, %s, %s::jsonb)",
        (user_id, run_id, "output", json.dumps(artifact)),
    )
    audit.record(user_id, "agent_run", "agent_run", run_id, {"status": status})
