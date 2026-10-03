# UX architecture — login to apply

Review of the current Job-hunt workspace against Demo 1 intent ([locked-intent.md](locked-intent.md)). This is the product flow candidates should feel; gaps call out what Demo 1 work closes.

## Primary journey (target)

```text
Sign in
  → Profile (skills, DS+AI titles, cities, CTC, deal-breakers)
  → Sources (connect Gmail; enable LinkedIn + ATS refresh)
  → Discover / Autopilot (daily multi-source refresh)
  → Review Inbox (ruthless ranked matches + evidence)
  → Prepare (approve → fact-gated CV / cover / answers)
  → Ready to apply
       ├─ ATS / career / Workday → Open apply URL + materials pack (candidate submits)
       └─ Recruiter email → Draft subject/body + resume (candidate sends)
  → Applications (track outcome)  [planned surface]
```

Free users stop at browse/rank/manual apply. Pro unlocks high-match emphasis, recruiter intel, and prepare/draft agents — still human-approved.

## Current IA (shell)

| Route | Surface | Role in journey | Maturity |
| --- | --- | --- | --- |
| `/sign-in` | Clerk or test token | Auth | Live |
| `/` | Dashboard | “What needs me today?” | Live (thin) |
| `/settings` | Profile | Targeting + verified facts | Live |
| `/sources` | Connectors | Consent + sync | Live (Gmail); LinkedIn Demo 1 |
| `/discover` | Search + queue scans | Active discovery / Demo 1 refresh | Live (fixture-heavy) |
| `/inbox` | Review Inbox | Ranked evidence + actions → apply | Live (core) |
| `/documents` | Tailored drafts | Inspect CV/cover/answers | Live |
| `/applications` | Tracker | Post-apply stages | **Planned stub** |
| `/agents` | Agent runs | Ops transparency | Live (debug-leaning) |
| `/analytics` | Funnel | Learning | Planned |

**UX judgment:** Nine nav items is too many for a switcher’s first week. Demo 1 should emphasize **Profile → Sources → Discover → Inbox → Documents**. Demote Agents/Analytics visually; treat Applications as “coming soon” until tracker exists.

## Step-by-step UX critique

### 1. Login
- **Works:** Clerk when configured; local test token otherwise.
- **Gap:** No post-login onboarding checklist (“Save profile → Connect sources → Run Demo 1 refresh”). Dashboard empty state should be that checklist, not a wall of empty cards.

### 2. Profile
- **Works:** Full India targeting fields; save triggers rematch.
- **Gap:** Defaults still generic “GenAI/Backend”. Demo 1 should seed **DS+AI title set** and remote/hybrid language. Verified facts as free-text lines is power-user; OK for beta, not for mass Free.

### 3. Sources
- **Works:** Honest catalog vs live labels; Gmail connect/sync/revoke.
- **Gap:** LinkedIn was catalog-only; Demo 1 adds LinkedIn ingest (fixture/recorded scrape path first). Candidate should see three Demo 1 sources side by side: Gmail, LinkedIn, Public ATS.

### 4. Discover / Autopilot
- **Works:** Queue fixture ATS; upload LinkedIn export JSON.
- **Gap:** Feels like an engineer console. Need one primary CTA: **“Refresh my matches (Gmail + LinkedIn + ATS)”** that queues all three and points to Inbox. Title/city filters stay secondary.

### 5. Review Inbox (spine)
- **Works:** Score, breakdown, risks, evidence, reject/save, prepare → approve → tailored → ready → handoff.
- **Gap:** Action labels are snake_case (`prepare_application`). Apply pack (CV + cover + JD overview) should sit on the detail pane when `ready_to_apply`, not only on Documents. Recruiter-email draft entry should appear when `extracted_emails` exist.

### 6. Documents
- **Works:** Lists fact-gated drafts.
- **Gap:** No inline preview of content in the list; candidate must trust status. Detail preview belongs here or in Inbox apply pack.

### 7. Apply handoff
- **Works:** Opens external URL; audit; never auto-submit.
- **Gap:** Handoff does not yet attach a visible materials checklist in the new tab context (clipboard/download). Demo 1 should show pack on-screen before open. Email path: Krishna draft API exists; Inbox needs a “Draft recruiter email” button when emails are present.

### 8. Applications
- **Missing:** After handoff, nowhere to mark Applied / Interview. Dashboard “by stage” is placeholder. Required before closed beta metrics for “applications started.”

## Information architecture recommendation (Demo 1)

```text
Primary nav (always):
  Today | Inbox | Discover | Sources | Profile

Secondary / later:
  Documents (linked from Inbox) | Applications | Agents | Analytics
```

Mental model for copy:

1. **Find** — Sources + Discover autopilot  
2. **Filter** — Inbox ranking  
3. **Prepare** — Approvals + Documents  
4. **Apply** — Handoff / email draft (you click send)  

## Trust & ethics in the UI

- Never claim LinkedIn is “partner live” until code + tests + honest status say so. Demo 1 uses `ingestion_ready` / recorded fixtures; live scrape stays flagged.
- Every external action repeats: **You submit. We never auto-send.**
- Source evidence (URL, excerpt, capture method) stays visible on every strong match.

## Success of this flow for closed beta

A beta user should complete without docs:

1. Sign in → save DS+AI profile (<3 min)  
2. One-click Demo 1 refresh  
3. Open Inbox, understand why a role scored high  
4. Save or reject; optionally prepare → approve → open apply  

If they bounce before step 3, IA failed — not matching quality.
