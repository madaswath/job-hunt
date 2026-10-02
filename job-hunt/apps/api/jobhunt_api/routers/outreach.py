from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import outreach

router = APIRouter(tags=["outreach"])


class DraftIn(BaseModel):
    inbox_item_id: str
    channel: str = "email"
    body: str | None = None
    explicit_outreach_request: bool = Field(default=True)


@router.get("/outreach/drafts")
def list_drafts(user: dict = Depends(current_user)) -> dict:
    rows = db.fetch_all(
        """
        SELECT id, inbox_item_id, channel, body, status, created_at
        FROM outreach_drafts
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (user["user_id"],),
    )
    return {"drafts": rows}


@router.post("/outreach/drafts")
def create_draft(body: DraftIn, user: dict = Depends(current_user)) -> dict:
    try:
        draft = outreach.create_outreach_draft(
            user["user_id"],
            inbox_item_id=body.inbox_item_id,
            channel=body.channel,
            body=body.body,
            explicit_request=body.explicit_outreach_request,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"draft": draft}
