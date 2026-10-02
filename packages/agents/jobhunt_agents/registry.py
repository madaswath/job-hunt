from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentDef:
    name: str
    role: str
    status: str
    allowed_tools: tuple[str, ...]
    requires: tuple[str, ...] = field(default_factory=tuple)


AGENTS: dict[str, AgentDef] = {
    "vishwakarma": AgentDef(
        "vishwakarma",
        "Workflow orchestrator",
        "live",
        ("transition_inbox", "record_audit", "enqueue_approval"),
        ("cannot_bypass_approval",),
    ),
    "narada": AgentDef("narada", "Discovery", "live", ("connector_ingest", "normalize_capture")),
    "ganesha": AgentDef("ganesha", "Qualification", "live", ("apply_hard_filters",)),
    "arjuna": AgentDef("arjuna", "Deterministic matching", "live", ("score_match_v2",)),
    "brihaspati": AgentDef("brihaspati", "Job/company analysis", "planned", ("analyze_job",), ("candidate_approval",)),
    "saraswati": AgentDef("saraswati", "Resume intelligence", "live", ("generate_document",), ("dharma_gate",)),
    "dharma": AgentDef("dharma", "Fact verification", "live", ("fact_gate",)),
    "hanuman": AgentDef("hanuman", "Recruiter intelligence", "planned", ("research_recruiter",), ("explicit_outreach_request",)),
    "krishna": AgentDef("krishna", "Outreach drafting", "live", ("create_outreach_draft",), ("explicit_outreach_request", "never_send")),
    "skanda": AgentDef("skanda", "Interview preparation", "planned", ("prepare_interview",), ("interview_stage_recorded",)),
    "lakshmi": AgentDef("lakshmi", "Career analytics", "planned", ("aggregate_analytics",), ("aggregates_and_explicit_feedback_only",)),
}
