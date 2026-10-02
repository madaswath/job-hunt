from fastapi import Depends, Header, HTTPException

from jobhunt_api.auth import current_user
from jobhunt_api.settings import settings


def require_uat_admin(
    user: dict = Depends(current_user),
    x_uat_signoff_secret: str = Header(default=""),
) -> dict:
    if not settings.uat_signoff_secret or x_uat_signoff_secret != settings.uat_signoff_secret:
        raise HTTPException(403, "invalid UAT sign-off secret")
    allowed = {uid.strip() for uid in settings.uat_admin_user_ids.split(",") if uid.strip()}
    if not allowed:
        raise HTTPException(503, "UAT admin allowlist not configured")
    if user["user_id"] not in allowed:
        raise HTTPException(403, "UAT sign-off requires an authorized administrator")
    return user
