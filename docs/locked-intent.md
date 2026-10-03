# Locked product intent

Source: founder interview (cloud agent session). Treat this as the north star for Demo 1 and freemium design. If this conflicts with older phase notes, **this file wins** until explicitly revised.

## Outcome

Ship a **paid** India-first job-search SaaS for a large audience of switchers. Not a personal job-search tool. Not portfolio-only.

## ICP

- Primary payers: **1–4 YOE** and **mid-level** professionals **switching roles**
- Pain: hopping many portals kills focus; they need one place that filters hard to their profile

## Beta vertical and market

- Titles (broad DS+AI): Data Scientist, Data Analyst, Analytics Engineer, ML Engineer, Applied Scientist, MLOps, GenAI / LLM / AI Engineer
- Geography: **India primary**; abroad roles listed; **any city** plus **remote** and **hybrid**

## Product spine (Free must deliver this or it is “another job portal”)

1. **One inbox** for job alerts / discovered listings  
2. **Ruthless filter** from user profile / skillset (match ranking)  
3. **Autopilot daily refresh**

## Sources — Demo 1 (all three in first demo)

| Source | Role in Demo 1 |
| --- | --- |
| Gmail job alerts | Ingest alerts, follow/scrape linked JD pages, normalize, rank into inbox |
| LinkedIn | Recorded LinkedIn-shaped listings → **shared indexed job DB** (Demo 1 `ingestion_ready`); unrestricted live scrape remains forbidden; partnerships later |
| Public ATS / career boards | Same shared index + per-user ranking |

Later (post-scale): official partnerships with job portals. Founder accepts LinkedIn scrape risk for Demo 1 / early product; partnerships are the long-term path.

**Architecture note:** prefer a **shared jobs index** with per-user ranking over purely per-user capture silos.

## Freemium

| | Free | Pro |
| --- | --- | --- |
| Listings | Broad access; user reviews matches and applies manually | High-match emphasis; recruiter emails / feed-style posts |
| Apply help | Manual | Bots prepare; **human reviews decisions** |
| Docs | — | CV tailor + resume review |
| Price (INR) | ₹0 | ₹199 / mo · ₹399 / qtr · ₹599 / half-year · ₹999 / year |

## Apply / outreach hard line

- External career site / Workday / ATS: **redirect** with tailored resume, cover letter, and JD overview — user submits  
- Recruiter email path: **draft** subject + body + tailored resume — user reviews and sends  
- **Never** silent auto-submit or auto-send

## Near-term success

1. **Local demo:** Gmail + LinkedIn + ATS → shared index → ranked inbox for a DS+AI test profile  
2. **Closed beta:** ~10–20 real switchers  

### Beta metrics (defaults until revised)

- ≥60% of beta users open the app ≥4 days/week  
- ≥5 saves / “interested” per active user per week  
- ≥3 applications started from the inbox per active user per week  

## Explicitly defer past Demo 1 / early beta

Interview prep agents, follow-up bots as a growth pillar, billing polish, portal partnerships, full analytics suite — after ranked inbox works for real humans.

## Conflict with older spec

`docs/product-spec.md` currently forbids unapproved marketplace scraping and keeps LinkedIn as catalog. **Founder override for this product direction:** LinkedIn ingest/scrape is in Demo 1. Update connectors/policy docs when implementation lands; keep honest live vs catalog labels in the UI.
