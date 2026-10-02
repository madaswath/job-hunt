from fastapi import APIRouter, Depends
from jobhunt_agents.registry import AGENTS

from jobhunt_api import db
from jobhunt_api.auth import current_user

router = APIRouter(tags=["agents"])


@router.get("/agents")
def list_agents(user: dict = Depends(current_user)) -> dict:
    runs = db.fetch_all(
        "SELECT * FROM agent_runs WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user["user_id"],),
    )
    return {
        "agents": [
            {
                "name": a.name,
                "role": a.role,
                "status": a.status,
                "allowed_tools": list(a.allowed_tools),
                "requires": list(a.requires),
            }
            for a in AGENTS.values()
        ],
        "runs": runs,
    }
