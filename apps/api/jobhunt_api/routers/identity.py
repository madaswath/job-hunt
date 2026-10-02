from fastapi import APIRouter, Depends

from jobhunt_api.auth import current_user

router = APIRouter(tags=["identity"])


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {"user_id": user["user_id"], "email": user["email"], "name": user["name"]}
