from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import approvals

router = APIRouter(tags=["approvals"])


class DecideIn(BaseModel):
    decision: str


@router.get("/approvals")
def list_approvals(user: dict = Depends(current_user)) -> dict:
    pending = approvals.list_pending(user["user_id"])
    all_rows = db.fetch_all(
        "SELECT * FROM approval_tasks WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user["user_id"],),
    )
    return {"approvals": all_rows, "pending": pending}


@router.post("/approvals/{task_id}/decide")
def decide(task_id: str, body: DecideIn, user: dict = Depends(current_user)) -> dict:
    try:
        return approvals.decide(user["user_id"], task_id, body.decision)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
