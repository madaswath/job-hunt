from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from jobhunt_domain.application_states import APPLICATION_STATES
from jobhunt_api.auth import current_user
from jobhunt_api.services import applications as app_svc

router = APIRouter(tags=["applications"])


class ApplicationCreateIn(BaseModel):
    inbox_item_id: str
    apply_url: str | None = None
    notes: str | None = None
    mark_inbox_applied: bool = False


class ApplicationPatchIn(BaseModel):
    state: str = Field(..., description="started | applied | interview | offer | rejected | withdrawn")
    notes: str | None = None


@router.get("/applications")
def list_applications(user: dict = Depends(current_user)) -> dict:
    items = app_svc.list_applications(user["user_id"])
    return {
        "status": "live",
        "items": items,
        "by_stage": app_svc.counts_by_stage(user["user_id"]),
        "states": list(APPLICATION_STATES),
    }


@router.get("/applications/{application_id}")
def get_application(application_id: str, user: dict = Depends(current_user)) -> dict:
    row = app_svc.get_application(user["user_id"], application_id)
    if not row:
        raise HTTPException(404, "not found")
    return {"item": row}


@router.post("/applications")
def create_application(body: ApplicationCreateIn, user: dict = Depends(current_user)) -> dict:
    """Track an application started from an inbox item (manual Free path or post-handoff)."""
    try:
        item = app_svc.create_or_get_from_inbox(
            user["user_id"],
            body.inbox_item_id,
            apply_url=body.apply_url,
            notes=body.notes,
            mark_inbox_applied=body.mark_inbox_applied,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    return {"item": item}


@router.patch("/applications/{application_id}")
def patch_application(application_id: str, body: ApplicationPatchIn, user: dict = Depends(current_user)) -> dict:
    try:
        item = app_svc.update_state(user["user_id"], application_id, body.state, body.notes)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"item": item}
