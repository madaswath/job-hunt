# LinkedIn scraper export drop folder

Use the bundled browserless scraper, then ingest into the shared master index.

## Scrape (your script, now in-repo)

```bash
# One keyword — 100 jobs + up to 15 hiring posts → data/linkedin-exports/<Keyword>/
python scripts/linkedin_browserless_scraper.py \
  --query "Data Scientist" --location India --limit 100 --posts --posts-limit 15

# All Demo 1 DS+AI keywords
python scripts/run_linkedin_scrape_batch.py --location India --jobs 100 --posts 15

# Then load master DB + match inbox
python scripts/run_linkedin_scrape_batch.py --skip-scrape --ingest --user-id user_test_1
```

Optional: `linkedin_session.json` (cookie export) improves feed-post search; guest job search works without it.

## Output files Job-hunt reads

Per keyword folder (`data/linkedin-exports/Data Scientist/`):

| File | Used |
| --- | --- |
| `results.json` / `jobs.json` | Primary (jobs + posts) |
| `jobs_clean.csv` | Jobs fallback / agent sheets |
| `recruiter_posts_drafts.csv` / `posts.clean.csv` | Hiring posts |

## Caps on ingest

- **Jobs:** latest **100 per keyword**
- **Feed posts:** **10–15** ranked to profile skills / target titles
- **`email_draft` / subject:** stripped on ingest (contact email kept; drafts are not facts)

## Ingest without re-scrape

```bash
python scripts/ingest_linkedin_export.py --dir data/linkedin-exports --dry-run
python scripts/ingest_linkedin_export.py --dir data/linkedin-exports --user-id user_test_1 --match
```

Or Discover UI → **Ingest LinkedIn exports to master DB**.
