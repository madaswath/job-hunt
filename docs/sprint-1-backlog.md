# Sprint 1 backlog — 2 October 2026

P0/P1 work is ported onto `develop` (created from `job-hunt-standalone`). `chore/add-job-hunt` is not used for further feature work.

## Branch policy

| Branch | Role |
|---|---|
| `job-hunt-standalone` | Beta/release. Merge only through reviewed PRs after sprint acceptance. |
| `develop` | Sprint integration. |
| `feature/<epic>-<story>` | Short-lived implementation. |
| `hotfix/<issue>` | Release-blocking corrections. |

## Founder decisions (accepted 2 October 2026)

- **Market:** India-first, with a global-ready schema.
- **Beta:** Invite-only and free. Activate billing after usage and conversion data exist.
- **Documents:** HTML preview plus downloadable DOCX and PDF.
- **Retention:** raw captures 30 days; Gmail-derived evidence 30 days; inactive jobs 90 days; normalized analytics retained without unnecessary personal content.
- **Owners:** Backend/Data, Frontend, AI, QA and DevOps seats are assigned even if one person holds multiple roles.

## P0 / P1 findings

| ID | Sev | Finding | Status |
|---|---|---|---|
| P0-01 | P0 | Frontend `api()` token selection used `A \|\| B ? C : D` | Closed on `develop` |
| P0-02 | P0 | Profile export/delete sent only `jobhunt_test_token` | Closed on `develop` |
| P0-03 | P0 | Document generation did not require an approved task | Closed on `develop` |
| P0-04 | P0 | Inbox prepare/draft-approval ignored current state | Closed on `develop` |
| P0-05 | P0 | Scan claim lacked `FOR UPDATE SKIP LOCKED` | Closed on `develop` |
| P0-06 | P0 | Outbox used select-then-update | Closed on `develop` |
| P0-07 | P0 | Ingestion was not transactional | Closed on `develop` |
| P1-01 | P1 | Gmail ingest query was untyped | Closed on `develop` |
| P1-02 | P1 | Catalogue contracts were tenant-scan shaped | Closed on `develop` |
| P1-03 | P1 | No source capability matrix | Closed on `develop` |
| P1-04 | P1 | No shared catalogue, source registry or scheduled ATS adapters | Open — `feature/e5-shared-catalogue` |
| P1-05 | P1 | Worker claim has no `leased_by` / heartbeat identity | Open |

## Integration failures closed before catalogue work

- Candidate-initiated imports are reviewable on `job-hunt-standalone`: `untrusted_source` is a risk, not an inbox-blocking hard filter.
- Browser capture already allows `connect` on standalone.
- `IngestIn` now preserves `use_gmail_api` so `FEATURE_EXTERNAL_GMAIL` and UAT sign-off actually gate live Gmail ingest.

## Epics E1–E10

| Epic | Owner seat | Sprint | Current baseline |
|---|---|---|---|
| E1 Enterprise foundation | Tech lead / DevOps | 1 | P0 queue/auth/UoW closed on `develop`. |
| E2 Candidate profile | Backend / AI | 1 | Structured facts live. Resume upload next. |
| E3 Source registry | Backend/Data | 1–2 | Shared registry tables in catalogue PR. |
| E4 Ingestion adapters | Backend/Data | 1–2 | Fixture ATS / Gmail / capture live. Scheduled ATS next. |
| E5 Canonical catalogue | Backend/Data | 1–2 | First Sprint 1 feature PR. |
| E6 Matching and local index | Backend / Frontend | 2–3 | Match v2 live. Match v3 + IndexedDB next. |
| E7 Tailoring | AI / Backend | 3 | Template drafts + Dharma. HTML/DOCX/PDF after approval. |
| E8 Application lifecycle | Backend / Frontend | 4 | External apply handoff only. |
| E9 Commercial controls | Product / Backend | 4 | Invite-only free beta; billing later. |
| E10 Operations/privacy | DevOps / QA | 1–4 | Retention defaults above. Admin catalogue ops next. |
