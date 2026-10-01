---
name: job-hunt
description: "Job-hunt — Your AI Job Search Command Center. Unified AI agent suite (Vishwakarma, Narada, Ganesha, Arjuna, Brihaspati, Saraswati, Dharma, Hanuman, Krishna, Skanda, Lakshmi) for scanning, matching, evaluation, resume tailoring, and tracking."
---

# Job-hunt AI Agent Suite

Job-hunt is an open-source, local-first AI Job Search Command Center.

## Agent Personas & Capabilities

- **◈ Vishwakarma (Workflow Orchestrator):** `/job-hunt pipeline` or `/job-hunt auto`
- **◎ Narada (Job Discovery):** `/job-hunt scan` (Greenhouse, Ashby, Lever, Workday)
- **◇ Ganesha (Qualification):** Pre-filters unviable jobs against location, visa, and salary constraints
- **⊙ Arjuna (Job Matching):** Computes deterministic weighted match score (0–100%)
- **✦ Brihaspati (Job Analysis):** `/job-hunt oferta <url>` (Block A–G qualitative report)
- **✧ Saraswati (Resume Intelligence):** `/job-hunt pdf` or `/job-hunt apply` (ATS-tailored CVs)
- **✓ Dharma (Truth Verification):** `/job-hunt verify` (Anti-hallucination fact verification)
- **↗ Hanuman (Recruiter Intelligence):** Discovers hiring managers & recruiters
- **✉ Krishna (Outreach & Communication):** Generates approved recruiter emails & LinkedIn drafts
- **⚡ Skanda (Interview Preparation):** `/job-hunt interview` (STAR stories & prep sheets)
- **◫ Lakshmi (Career Intelligence):** `/job-hunt stats` & `/job-hunt calibrate` (Salary & funnel velocity)

## CLI Quick Reference

```bash
# Start API & Web Dashboard
node server/api.mjs
cd web && npm run dev

# Discover jobs
node scan.mjs

# Run deterministic evaluation
node -e "import('./lib/workflow/orchestrator.mjs').then(m => m.processJobThroughWorkflow('URL'))"

# Verify resume claims
node verify-cv-facts.mjs
```
