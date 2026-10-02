import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jobhunt_api.settings import settings

router = APIRouter(tags=["dev"])


class DevTokenIn(BaseModel):
    user_id: str = "user_test_1"
    email: str = "candidate@example.com"
    name: str = "Test Candidate"


@router.post("/dev/token")
def dev_token(body: DevTokenIn) -> dict:
    if settings.auth_mode != "test":
        raise HTTPException(404, "not found")
    token = jwt.encode(
        {"sub": body.user_id, "email": body.email, "name": body.name},
        settings.test_jwt_secret,
        algorithm="HS256",
    )
    return {"token": token}
