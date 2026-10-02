from fastapi import APIRouter, Depends, HTTPException
from jobhunt_domain.ctc import normalize_ctc_inr_annual
from jobhunt_domain.india import INDIA_CITIES, ROLE_ALIASES
from pydantic import BaseModel, Field

from jobhunt_api import db
from jobhunt_api.auth import current_user
from jobhunt_api.services import audit, rematch
from jobhunt_api.services.profile_loader import load_verified_fact_rows
from jobhunt_api.settings import settings

router = APIRouter(tags=["profile"])

FACT_KINDS = ("skill", "title", "employer", "education", "metric", "other")


class VerifiedFactIn(BaseModel):
    kind: str = "other"
    value: str


class ProfileIn(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    headline: str | None = None
    skills: list[str] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list)
    title_aliases: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    work_mode: str = "hybrid"
    current_ctc_inr_annual: float | None = None
    expected_ctc_inr_annual: float | None = None
    min_ctc_inr_annual: float | None = None
    min_ctc_inr_monthly: float | None = None
    notice_period_days: int | None = None
    joining_date: str | None = None
    employment_types: list[str] = Field(default_factory=lambda: ["full-time"])
    company_preference: str = "either"
    deal_breakers: list[str] = Field(default_factory=list)
    banned_companies: list[str] = Field(default_factory=list)
    banned_roles: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    seniority: str | None = None
    verified_facts: list[VerifiedFactIn] = Field(default_factory=list)
    trigger_rematch: bool = True


@router.get("/profile")
def get_profile(user: dict = Depends(current_user)) -> dict:
    row = db.fetch_one("SELECT * FROM candidate_profiles WHERE user_id = %s", (user["user_id"],))
    facts = load_verified_fact_rows(user["user_id"])
    return {
        "profile": row,
        "verified_facts": facts,
        "defaults": {"cities": INDIA_CITIES, "role_aliases": ROLE_ALIASES, "fact_kinds": list(FACT_KINDS)},
        "feature_us_market": settings.feature_us_market,
    }


@router.put("/profile")
def put_profile(body: ProfileIn, user: dict = Depends(current_user)) -> dict:
    data = body.model_dump()
    facts = data.pop("verified_facts")
    trigger_rematch = data.pop("trigger_rematch", True)
    if data.get("min_ctc_inr_monthly") is not None and data.get("min_ctc_inr_annual") is None:
        data["min_ctc_inr_annual"] = normalize_ctc_inr_annual(data.pop("min_ctc_inr_monthly"), "monthly")
    else:
        data.pop("min_ctc_inr_monthly", None)
    joining = data.get("joining_date") or None
    db.execute(
        """
        INSERT INTO candidate_profiles (
          user_id, full_name, email, phone, headline, skills, target_titles, title_aliases,
          preferred_cities, work_mode, current_ctc_inr_annual, expected_ctc_inr_annual, min_ctc_inr_annual,
          notice_period_days, joining_date, employment_types, company_preference, deal_breakers,
          banned_companies, banned_roles, years_experience, seniority
        ) VALUES (
          %(user_id)s, %(full_name)s, %(email)s, %(phone)s, %(headline)s, %(skills)s, %(target_titles)s, %(title_aliases)s,
          %(preferred_cities)s, %(work_mode)s, %(current_ctc_inr_annual)s, %(expected_ctc_inr_annual)s, %(min_ctc_inr_annual)s,
          %(notice_period_days)s, %(joining_date)s, %(employment_types)s, %(company_preference)s, %(deal_breakers)s,
          %(banned_companies)s, %(banned_roles)s, %(years_experience)s, %(seniority)s
        )
        ON CONFLICT (user_id) DO UPDATE SET
          full_name = EXCLUDED.full_name, email = EXCLUDED.email, phone = EXCLUDED.phone, headline = EXCLUDED.headline,
          skills = EXCLUDED.skills, target_titles = EXCLUDED.target_titles, title_aliases = EXCLUDED.title_aliases,
          preferred_cities = EXCLUDED.preferred_cities, work_mode = EXCLUDED.work_mode,
          current_ctc_inr_annual = EXCLUDED.current_ctc_inr_annual, expected_ctc_inr_annual = EXCLUDED.expected_ctc_inr_annual,
          min_ctc_inr_annual = EXCLUDED.min_ctc_inr_annual, notice_period_days = EXCLUDED.notice_period_days,
          joining_date = EXCLUDED.joining_date, employment_types = EXCLUDED.employment_types,
          company_preference = EXCLUDED.company_preference, deal_breakers = EXCLUDED.deal_breakers,
          banned_companies = EXCLUDED.banned_companies, banned_roles = EXCLUDED.banned_roles,
          years_experience = EXCLUDED.years_experience, seniority = EXCLUDED.seniority, updated_at = now()
        """,
        {**data, "user_id": user["user_id"], "joining_date": joining},
    )
    db.execute("DELETE FROM verified_facts WHERE user_id = %s", (user["user_id"],))
    for fact in facts:
        kind = fact["kind"] if isinstance(fact, dict) else fact.kind
        value = fact["value"] if isinstance(fact, dict) else fact.value
        if kind not in FACT_KINDS:
            kind = "other"
        db.execute(
            "INSERT INTO verified_facts (user_id, kind, value, source, verified) VALUES (%s, %s, %s, 'manual', true)",
            (user["user_id"], kind, value),
        )
    audit.record(user["user_id"], "profile_updated", "candidate_profile", user["user_id"])
    rematch_job_id = rematch.enqueue_rematch(user["user_id"]) if trigger_rematch else None
    return {**get_profile(user), "rematch_job_id": rematch_job_id}


@router.post("/profile/facts")
def add_fact(body: VerifiedFactIn, user: dict = Depends(current_user)) -> dict:
    if body.kind not in FACT_KINDS:
        raise HTTPException(400, "invalid fact kind")
    row = db.fetch_one(
        """
        INSERT INTO verified_facts (user_id, kind, value, source, verified)
        VALUES (%s, %s, %s, 'manual', true)
        RETURNING id, kind, value, source, verified
        """,
        (user["user_id"], body.kind, body.value),
    )
    audit.record(user["user_id"], "fact_added", "verified_fact", str(row["id"]))
    return {"fact": row}


@router.delete("/profile/facts/{fact_id}")
def delete_fact(fact_id: str, user: dict = Depends(current_user)) -> dict:
    db.execute("DELETE FROM verified_facts WHERE id = %s AND user_id = %s", (fact_id, user["user_id"]))
    audit.record(user["user_id"], "fact_deleted", "verified_fact", fact_id)
    return {"deleted": fact_id}


@router.post("/profile/export")
def export_profile(user: dict = Depends(current_user)) -> dict:
    from jobhunt_api.services import privacy

    audit.record(user["user_id"], "export_requested", "candidate_profile", user["user_id"])
    return {"status": "ready", "export": privacy.export_user_data(user["user_id"])}


class DeleteConfirm(BaseModel):
    confirm: bool = False


@router.post("/profile/delete")
def delete_profile(body: DeleteConfirm, user: dict = Depends(current_user)) -> dict:
    from jobhunt_api.services import privacy

    if not body.confirm:
        raise HTTPException(400, "set confirm=true to delete all candidate data")
    audit.record(user["user_id"], "deletion_requested", "app_user", user["user_id"])
    return privacy.wipe_user(user["user_id"])
