export interface AgentInfo {
  id: string;
  name: string;
  title: string;
  role: string;
  icon: string;
  status: string;
  module: string;
  tools?: string[];
  skills: string[];
}

export const AGENTS: Record<string, AgentInfo> = {
  orchestrator: {
    id: "vishwakarma",
    name: "Vishwakarma",
    title: "Master Workflow Orchestrator",
    role: "Coordinates end-to-end pipeline execution from discovery to application",
    icon: "◈",
    status: "ACTIVE",
    module: "lib/workflow/orchestrator.mjs",
    skills: ["Stage sequencing", "Retry policies", "Error recovery", "Token budget allocation"],
  },

  discovery: {
    id: "narada",
    name: "Narada",
    title: "Job Discovery Agent",
    role: "Scans 100+ public ATS platforms (Greenhouse, Ashby, Lever, Workday) and career boards",
    icon: "◎",
    status: "READY",
    module: "scan.mjs",
    tools: ["Greenhouse", "Lever", "Ashby", "Workday", "Breezy", "RemoteOK", "HN", "Interamt"],
    skills: ["Zero-token ingestion", "Rate limiting", "RSS parsing", "Deduplication"],
  },

  qualification: {
    id: "ganesha",
    name: "Ganesha",
    title: "Qualification Agent",
    role: "Removes unsuitable postings and clears hard eligibility/location/visa gates",
    icon: "◇",
    status: "READY",
    module: "lib/matching/qualification-engine.mjs",
    skills: ["Seniority filtering", "Location compatibility", "Visa sponsorship check", "Salary floor evaluation"],
  },

  matching: {
    id: "arjuna",
    name: "Arjuna",
    title: "Job Matching Agent",
    role: "Computes multi-dimensional, explainable weighted match scores against user profile",
    icon: "⊙",
    status: "READY",
    module: "lib/matching/deterministic-scorer.mjs",
    skills: ["Technical skills (30%)", "Experience & Seniority (20%)", "Domain alignment (15%)", "Cloud infra (15%)"],
  },

  analysis: {
    id: "brihaspati",
    name: "Brihaspati",
    title: "Strategic Job Analysis Agent",
    role: "Deep qualitative analysis of JD requirements, growth opportunities, and hidden risks",
    icon: "✦",
    status: "READY",
    module: "modes/oferta.md",
    skills: ["Block A-F evaluation", "Posting Legitimacy (Tier 1-4)", "Risk synthesis", "Keyword extraction"],
  },

  resume: {
    id: "saraswati",
    name: "Saraswati",
    title: "Resume Intelligence Agent",
    role: "Tailors ATS-optimized, high-impact HTML, PDF, and LaTeX CVs with exact JD alignment",
    icon: "✧",
    status: "READY",
    module: "build-cv-html.mjs",
    skills: ["ATS layout formatting", "PDF compilation via Playwright", "LaTeX generation", "Executive summary tailoring"],
  },

  verification: {
    id: "dharma",
    name: "Dharma",
    title: "Truth Verification Agent",
    role: "Strict gatekeeper enforcing anti-hallucination, metric provenance, and ATS compliance",
    icon: "✓",
    status: "PASSED",
    module: "verify-cv-facts.mjs",
    skills: ["Fact provenance tracing", "Metric verification", "ATS keyword validation", "Anti-fabrication enforcement"],
  },

  recruiter: {
    id: "hanuman",
    name: "Hanuman",
    title: "Recruiter Intelligence Agent",
    role: "Discovers Talent Acquisition leaders, Hiring Managers, and warm company connections",
    icon: "↗",
    status: "READY",
    module: "lib/recruiter/recruiter-finder.mjs",
    skills: ["Local contacts matching", "LinkedIn query builder", "Hiring manager resolution", "Affinity scoring"],
  },

  outreach: {
    id: "krishna",
    name: "Krishna",
    title: "Outreach & Communication Agent",
    role: "Drafts persuasive, evidence-backed recruiter messages with human approval gating",
    icon: "✉",
    status: "READY",
    module: "lib/outreach/outreach-service.mjs",
    skills: ["Contextual email drafting", "Proof point anchoring", "Gmail draft integration", "Follow-up cadence planning"],
  },

  interview: {
    id: "skanda",
    name: "Skanda",
    title: "Interview Preparation Agent",
    role: "Selects optimal STAR+R stories and prepares targeted company battlecards",
    icon: "⚡",
    status: "READY",
    module: "match-star.mjs",
    skills: ["STAR story retrieval", "Technical question bank", "Company red flag detection", "Post-interview debriefing"],
  },

  analytics: {
    id: "lakshmi",
    name: "Lakshmi",
    title: "Career Intelligence Agent",
    role: "Analyzes market salary benchmarks, pipeline funnel velocity, and ROI of negotiation",
    icon: "◫",
    status: "READY",
    module: "funnel-velocity.mjs",
    skills: ["Salary gap analysis", "Funnel velocity benchmarking", "Negotiation ROI talking points", "Skill gap heatmaps"],
  },
};
