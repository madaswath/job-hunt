from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunt_api.auth import current_user
from jobhunt_api.services import documents
from jobhunt_api.settings import settings

router = APIRouter(tags=["documents"])


class GenerateIn(BaseModel):
    inbox_item_id: str
    approval_task_id: str


@router.get("/documents")
def list_all(user: dict = Depends(current_user), inbox_item_id: str | None = None) -> dict:
    return {"items": documents.list_documents(user["user_id"], inbox_item_id)}


@router.post("/documents/generate")
def generate(body: GenerateIn, user: dict = Depends(current_user)) -> dict:
    if not settings.feature_document_drafts:
        raise HTTPException(503, "document drafts disabled")
    try:
        return documents.generate_drafts_for_inbox(user["user_id"], body.inbox_item_id, body.approval_task_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
