from jobhunt_domain.india import canonicalize_city
from jobhunt_domain.schemas import CandidateProfile, JobPosting


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def apply_hard_filters(job: JobPosting, profile: CandidateProfile) -> list[str]:
    reasons: list[str] = []
    company = _norm(job.company)
    title = _norm(job.title)

    if company and any(company == _norm(b) or _norm(b) in company for b in profile.banned_companies):
        reasons.append("banned_company")
    if title and any(_norm(b) and _norm(b) in title for b in profile.banned_roles):
        reasons.append("banned_role")

    if profile.seniority and job.seniority:
        cand = _norm(profile.seniority)
        role = _norm(job.seniority)
        seniority_rank = {
            "intern": 0,
            "junior": 1,
            "mid": 2,
            "senior": 3,
            "staff": 4,
            "principal": 5,
            "lead": 3,
        }
        if abs(seniority_rank.get(cand, 2) - seniority_rank.get(role, 2)) >= 3:
            reasons.append("seniority_mismatch")

    job_city = canonicalize_city(job.location)
    pref_cities = {canonicalize_city(c) for c in profile.preferred_cities if c}
    if pref_cities and job_city and job_city not in pref_cities and "remote" not in {c.lower() if isinstance(c, str) else c for c in pref_cities}:
        if _norm(job.work_mode) != "remote" and "remote" not in {(_norm(c) if c else "") for c in profile.preferred_cities}:
            reasons.append("location_mismatch")

    if profile.work_mode and job.work_mode:
        if _norm(profile.work_mode) == "remote" and _norm(job.work_mode) == "onsite":
            reasons.append("work_mode_mismatch")
        if _norm(profile.work_mode) == "onsite" and _norm(job.work_mode) == "remote":
            reasons.append("work_mode_mismatch")

    if profile.employment_types and job.employment_type:
        allowed = {_norm(t) for t in profile.employment_types}
        if _norm(job.employment_type) not in allowed:
            reasons.append("employment_type_mismatch")

    if profile.min_ctc_inr_annual is not None and job.ctc_inr_annual_max is not None:
        if job.ctc_inr_annual_max < profile.min_ctc_inr_annual:
            reasons.append("ctc_below_minimum")

    if profile.notice_period_days is not None and job.notice_period_days is not None:
        if job.notice_period_days < profile.notice_period_days:
            reasons.append("notice_period_conflict")

    if profile.joining_date and job.joining_date and job.joining_date < profile.joining_date:
        reasons.append("joining_date_conflict")

    haystack = " ".join([job.title, job.company or "", job.description]).lower()
    for breaker in profile.deal_breakers:
        if breaker and _norm(breaker) in haystack:
            reasons.append("deal_breaker")
            break

    return reasons
