from datetime import datetime, timezone

from jobhunt_domain.india import ROLE_ALIASES, canonicalize_city
from jobhunt_domain.qualification import apply_hard_filters
from jobhunt_domain.schemas import CandidateProfile, FactorScore, JobPosting, MatchResult

WEIGHTS = {
    "title": 0.20,
    "must_have_skills": 0.25,
    "adjacent_skills": 0.10,
    "seniority": 0.10,
    "location": 0.15,
    "ctc": 0.10,
    "employment_notice": 0.05,
    "company": 0.05,
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _title_score(job: JobPosting, profile: CandidateProfile) -> tuple[float, str]:
    targets = [_norm(t) for t in profile.target_titles + profile.title_aliases if t]
    title = _norm(job.title)
    if not targets or not title:
        return 0.4, "missing title signals"
    if any(t in title or title in t for t in targets):
        return 1.0, "direct title match"
    expanded: set[str] = set()
    for t in targets:
        expanded |= ROLE_ALIASES.get(t, {t})
    if any(alias in title for alias in expanded):
        return 0.85, "alias title match"
    return 0.2, "title weakly aligned"


def _overlap(needed: list[str], have: list[str]) -> tuple[list[str], list[str], float]:
    have_n = [_norm(s) for s in have]
    matched, missing = [], []
    for skill in needed:
        n = _norm(skill)
        if any(n in h or h in n for h in have_n if h):
            matched.append(skill)
        else:
            missing.append(skill)
    if not needed:
        return [], [], 0.5
    return matched, missing, len(matched) / len(needed)


def _freshness_hours(posted_at: str | None) -> float | None:
    if not posted_at:
        return None
    try:
        parsed = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600)
    except ValueError:
        return None


def score_match_v2(job: JobPosting, profile: CandidateProfile, evidence_ids: list[str] | None = None) -> MatchResult:
    hard = apply_hard_filters(job, profile)
    unknown: list[str] = []
    if not job.skills and not job.must_have_skills:
        unknown.append("job_skills")
    if profile.min_ctc_inr_annual is None or job.ctc_inr_annual_min is None:
        unknown.append("ctc")
    if not job.location:
        unknown.append("location")

    must = job.must_have_skills or job.skills
    adj = job.adjacent_skills
    matched_must, missing_must, must_score = _overlap(must, profile.skills)
    matched_adj, _, adj_score = _overlap(adj, profile.skills) if adj else ([], [], 0.5)

    title_s, title_r = _title_score(job, profile)

    if profile.years_experience is None and not profile.seniority:
        seniority_s, seniority_r = 0.5, "unknown seniority"
        unknown.append("seniority")
    else:
        seniority_s, seniority_r = 0.8, "experience within band"
        if profile.seniority and job.seniority and _norm(profile.seniority) != _norm(job.seniority):
            seniority_s, seniority_r = 0.55, "adjacent seniority"

    job_city = canonicalize_city(job.location)
    prefs = {canonicalize_city(c) for c in profile.preferred_cities if c}
    if _norm(job.work_mode) == "remote" or (job_city and job_city == "remote"):
        loc_s, loc_r = 1.0, "remote compatible"
    elif prefs and job_city and job_city in prefs:
        loc_s, loc_r = 1.0, "preferred city"
    elif not job.location:
        loc_s, loc_r = 0.4, "unknown location"
    else:
        loc_s, loc_r = 0.35, "city not preferred"

    if profile.min_ctc_inr_annual is None or (job.ctc_inr_annual_min is None and job.ctc_inr_annual_max is None):
        ctc_s, ctc_r = 0.5, "ctc unknown"
    else:
        mid = job.ctc_inr_annual_max or job.ctc_inr_annual_min or 0
        floor = profile.min_ctc_inr_annual or 0
        if mid >= floor:
            ctc_s, ctc_r = 1.0, "ctc meets minimum"
        else:
            ctc_s, ctc_r = 0.2, "ctc below minimum"

    emp_s, emp_r = 0.7, "employment compatible"
    if profile.employment_types and job.employment_type:
        if _norm(job.employment_type) in {_norm(t) for t in profile.employment_types}:
            emp_s, emp_r = 1.0, "employment type match"
        else:
            emp_s, emp_r = 0.2, "employment type mismatch"

    company_s, company_r = 0.7, "no company conflict"
    if profile.company_preference != "either" and job.company_type:
        if _norm(profile.company_preference) == _norm(job.company_type):
            company_s, company_r = 1.0, "company type match"
        else:
            company_s, company_r = 0.4, "company type differs"

    factors = [
        FactorScore(name="title", weight=WEIGHTS["title"], score=title_s, reason=title_r),
        FactorScore(name="must_have_skills", weight=WEIGHTS["must_have_skills"], score=must_score, reason="must-have overlap"),
        FactorScore(name="adjacent_skills", weight=WEIGHTS["adjacent_skills"], score=adj_score, reason="adjacent overlap"),
        FactorScore(name="seniority", weight=WEIGHTS["seniority"], score=seniority_s, reason=seniority_r),
        FactorScore(name="location", weight=WEIGHTS["location"], score=loc_s, reason=loc_r),
        FactorScore(name="ctc", weight=WEIGHTS["ctc"], score=ctc_s, reason=ctc_r),
        FactorScore(name="employment_notice", weight=WEIGHTS["employment_notice"], score=emp_s, reason=emp_r),
        FactorScore(name="company", weight=WEIGHTS["company"], score=company_s, reason=company_r),
    ]
    overall = round(sum(f.weight * f.score for f in factors) * 100, 2)
    if hard:
        overall = 0.0

    reasons = [f.reason for f in factors if f.score >= 0.8]
    risks = list(hard) + [f.reason for f in factors if f.score < 0.4]
    if not job.source_trusted:
        risks.append("untrusted_source")
    freshness = _freshness_hours(job.posted_at)
    known = 8 - len(set(unknown))
    confidence = round(max(0.2, min(0.99, known / 8)), 2)

    return MatchResult(
        overall_score=overall,
        confidence=confidence,
        breakdown=factors,
        matched_skills=sorted(set(matched_must + matched_adj)),
        missing_skills=missing_must,
        unknown_inputs=sorted(set(unknown)),
        reasons_to_apply=reasons[:6],
        risks=sorted(set(risks)),
        freshness_hours=freshness,
        evidence_ids=evidence_ids or [],
        passed_hard_filters=not hard,
        hard_filter_reasons=hard,
    )
