from fastapi import APIRouter, Depends, HTTPException

from jobhunt_api.auth import current_user

router = APIRouter()


def _planned(name: str):
    raise HTTPException(status_code=501, detail=f"{name} is planned, not live in Phase 1")


@router.get("/applications")
def applications(user: dict = Depends(current_user)):
    return {"status": "planned", "items": []}


@router.get("/analytics")
def analytics(user: dict = Depends(current_user)):
    return {"status": "planned", "metrics": {}}


@router.get("/billing")
def billing(user: dict = Depends(current_user)):
    return {"status": "planned", "plan": "free"}


@router.post("/billing/checkout")
def checkout(user: dict = Depends(current_user)):
    _planned("billing")


@router.get("/admin/tenants")
def admin(user: dict = Depends(current_user)):
    _planned("admin")
