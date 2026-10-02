from jobhunt_domain.ctc import normalize_ctc_inr_annual
from jobhunt_domain.matching import score_match_v2
from jobhunt_domain.qualification import apply_hard_filters
from jobhunt_domain.schemas import CandidateProfile, JobPosting


def profile() -> CandidateProfile:
    return CandidateProfile(
        skills=["python", "fastapi", "rag"],
        target_titles=["GenAI Engineer"],
        preferred_cities=["Bengaluru", "remote"],
        work_mode="hybrid",
        min_ctc_inr_annual=2_500_000,
        employment_types=["full-time"],
        years_experience=6,
        seniority="mid",
    )


def job(**kwargs) -> JobPosting:
    data = dict(
        title="GenAI Engineer",
        company="Example Labs",
        location="Bengaluru",
        work_mode="hybrid",
        employment_type="full-time",
        seniority="mid",
        skills=["python", "rag"],
        must_have_skills=["python", "rag"],
        adjacent_skills=["langchain"],
        ctc_inr_annual_min=2_500_000,
        ctc_inr_annual_max=4_000_000,
        source_trusted=True,
    )
    data.update(kwargs)
    return JobPosting(**data)


def test_ctc_normalize():
    assert normalize_ctc_inr_annual(2, "lpa") == 200_000
    assert normalize_ctc_inr_annual(200000, "monthly") == 2_400_000


def test_hard_filter_banned_and_ctc():
    p = profile()
    p.banned_companies = ["Example Labs"]
    assert "banned_company" in apply_hard_filters(job(), p)
    assert "ctc_below_minimum" in apply_hard_filters(job(ctc_inr_annual_max=1_000_000), profile())


def test_match_v2_strong():
    result = score_match_v2(job(), profile(), evidence_ids=["ev1"])
    assert result.passed_hard_filters
    assert result.overall_score >= 70
    assert result.evidence_ids == ["ev1"]
    names = [f.name for f in result.breakdown]
    assert names == [
        "title",
        "must_have_skills",
        "adjacent_skills",
        "seniority",
        "location",
        "ctc",
        "employment_notice",
        "company",
    ]
    assert abs(sum(f.weight for f in result.breakdown) - 1) < 1e-6


def test_match_v2_untrusted_source_is_risk_not_gate():
    result = score_match_v2(job(source_trusted=False), profile())
    assert result.overall_score > 0
    assert result.passed_hard_filters is True
    assert "untrusted_source" in result.risks
    assert "untrusted_source" not in result.hard_filter_reasons


def test_match_v2_hard_filter_zeroes_score():
    p = profile()
    p.banned_roles = ["intern"]
    blocked = score_match_v2(job(title="Intern GenAI Engineer"), p)
    assert blocked.overall_score == 0
    assert "banned_role" in blocked.hard_filter_reasons
