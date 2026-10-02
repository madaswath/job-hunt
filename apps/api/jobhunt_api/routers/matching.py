from fastapi import APIRouter, Depends
from jobhunt_domain.matching import score_match_v2
from jobhunt_domain.schemas import CandidateProfile, JobPosting
from pydantic import BaseModel

from jobhunt_api.auth import current_user

router = APIRouter(tags=["matching"])


class MatchPreviewIn(BaseModel):
    job: JobPosting
    profile: CandidateProfile


@router.post("/matching/preview")
def preview(body: MatchPreviewIn, user: dict = Depends(current_user)) -> dict:
    result = score_match_v2(body.job, body.profile)
    return result.model_dump()
