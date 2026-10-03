# LinkedIn scraper export drop folder

Point your scraping script here (or set `LINKEDIN_EXPORT_DIR`).

## Layout (recommended)

```text
data/linkedin-exports/
  Data Scientist/
    jobs.json          # or jobs.clean.csv
    posts.json         # or posts.clean.csv / feed_posts.csv
  GenAI Engineer/
    jobs.clean.csv
    posts.clean.csv
```

## Caps applied on ingest

- **Jobs:** most recent **100 per keyword/role**
- **Feed posts:** **10–15** ranked to user skills / target titles

## Jobs JSON shape (flexible aliases supported)

```json
{
  "metadata": { "keyword": "Data Scientist", "engine": "your-scraper" },
  "jobs": [
    {
      "job_id": "123",
      "title": "Data Scientist",
      "company": "Example",
      "location": "Bengaluru",
      "url": "https://www.linkedin.com/jobs/view/123",
      "description": "...",
      "posted_at": "2026-10-01T00:00:00Z",
      "workplace_type": "hybrid",
      "skills": ["python", "sql"],
      "emails": ["talent@example.com"],
      "application_urls": ["https://boards.example/apply/123"]
    }
  ],
  "posts": [
    {
      "post_id": "urn:li:activity:1",
      "author": "Hiring Manager",
      "content": "Hiring Data Scientists — python / ML. careers@example.com",
      "url": "https://www.linkedin.com/feed/update/urn:li:activity:1",
      "emails": ["careers@example.com"],
      "posted_at": "2026-10-01T12:00:00Z"
    }
  ]
}
```

## Clean CSV columns (any alias works)

Jobs: `job_id,title,company,location,url,description,posted_at,workplace_type,skills,emails,keyword`

Posts: `post_id,author,content,url,emails,company,posted_at,keyword`

## Ingest commands

```bash
# Parse + show caps only
python scripts/ingest_linkedin_export.py --dir data/linkedin-exports --dry-run

# Write master index + match into inbox
python scripts/ingest_linkedin_export.py --dir data/linkedin-exports --user-id user_test_1 --match

# Or via API (authenticated)
# POST /api/v1/discovery/linkedin-master-ingest
# { "jobs_per_keyword": 100, "posts_limit": 15, "match_into_inbox": true }
```

The API stores rows in `shared_jobs` (indexed master catalogue) then ranks strong matches into Review Inbox.
