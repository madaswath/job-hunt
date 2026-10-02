from jobhunt_domain.schemas import CandidateProfile

from jobhunt_api import db


def load_candidate_profile(user_id: str) -> CandidateProfile:
    row = db.fetch_one("SELECT * FROM candidate_profiles WHERE user_id = %s", (user_id,))
    if not row:
        return CandidateProfile()
    joining = row.get("joining_date")
    if joining is not None and hasattr(joining, "isoformat"):
        joining = joining.isoformat()
    return CandidateProfile(
        skills=list(row.get("skills") or []),
        target_titles=list(row.get("target_titles") or []),
        title_aliases=list(row.get("title_aliases") or []),
        preferred_cities=list(row.get("preferred_cities") or []),
        work_mode=row.get("work_mode") or "hybrid",
        min_ctc_inr_annual=row.get("min_ctc_inr_annual"),
        expected_ctc_inr_annual=row.get("expected_ctc_inr_annual"),
        notice_period_days=row.get("notice_period_days"),
        joining_date=str(joining) if joining else None,
        employment_types=list(row.get("employment_types") or ["full-time"]),
        company_preference=row.get("company_preference") or "either",
        deal_breakers=list(row.get("deal_breakers") or []),
        banned_companies=list(row.get("banned_companies") or []),
        banned_roles=list(row.get("banned_roles") or []),
        years_experience=row.get("years_experience"),
        seniority=row.get("seniority"),
    )


def load_verified_fact_values(user_id: str) -> list[str]:
    rows = db.fetch_all("SELECT value FROM verified_facts WHERE user_id = %s AND verified = true", (user_id,))
    return [r["value"] for r in rows]


def load_verified_fact_rows(user_id: str) -> list[dict]:
    return db.fetch_all(
        "SELECT id, kind, value, source, verified FROM verified_facts WHERE user_id = %s ORDER BY created_at",
        (user_id,),
    )


def profile_bits_for_gate(user_id: str) -> list[str]:
    row = db.fetch_one(
        "SELECT full_name, headline, skills, target_titles FROM candidate_profiles WHERE user_id = %s",
        (user_id,),
    )
    if not row:
        return []
    bits: list[str] = []
    if row.get("full_name"):
        bits.append(str(row["full_name"]))
    if row.get("headline"):
        bits.append(str(row["headline"]))
    for s in row.get("skills") or []:
        bits.append(str(s))
    for t in row.get("target_titles") or []:
        bits.append(str(t))
    return bits
