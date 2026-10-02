from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list)
    title_aliases: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    work_mode: str = "hybrid"
    min_ctc_inr_annual: float | None = None
    expected_ctc_inr_annual: float | None = None
    notice_period_days: int | None = None
    joining_date: str | None = None
    employment_types: list[str] = Field(default_factory=lambda: ["full-time"])
    company_preference: str = "either"
    deal_breakers: list[str] = Field(default_factory=list)
    banned_companies: list[str] = Field(default_factory=list)
    banned_roles: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    seniority: str | None = None


class JobPosting(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    adjacent_skills: list[str] = Field(default_factory=list)
    ctc_inr_annual_min: float | None = None
    ctc_inr_annual_max: float | None = None
    notice_period_days: int | None = None
    joining_date: str | None = None
    source_id: str | None = None
    source_trusted: bool = True
    company_type: str | None = None
    posted_at: str | None = None


class FactorScore(BaseModel):
    name: str
    weight: float
    score: float
    reason: str


class MatchResult(BaseModel):
    overall_score: float
    confidence: float
    breakdown: list[FactorScore]
    matched_skills: list[str]
    missing_skills: list[str]
    unknown_inputs: list[str]
    reasons_to_apply: list[str]
    risks: list[str]
    freshness_hours: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    passed_hard_filters: bool = True
    hard_filter_reasons: list[str] = Field(default_factory=list)
