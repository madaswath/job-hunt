from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunt_api.auth_admin import require_uat_admin
from jobhunt_api.services import production_gates

router = APIRouter(tags=["uat"])


class SignoffIn(BaseModel):
    component: str
    signed_by: str
    notes: str | None = None


@router.post("/uat/signoff")
def uat_signoff(body: SignoffIn, admin: dict = Depends(require_uat_admin)) -> dict:
    if body.component not in {"gmail_alerts"}:
        raise HTTPException(400, "unknown component")
    signed_by = body.signed_by or admin.get("user_id") or admin.get("email") or "admin"
    row = production_gates.record_uat_signoff(body.component, signed_by, body.notes)
    return {
        "signoff": row,
        "production_live": production_gates.gmail_production_live(),
        "signed_by_admin": admin["user_id"],
    }


@router.delete("/uat/signoff/{component}")
def uat_revoke_signoff(component: str, admin: dict = Depends(require_uat_admin)) -> dict:
    production_gates.revoke_uat_signoff(component, reason=f"admin:{admin['user_id']}")
    return {"revoked": component}
