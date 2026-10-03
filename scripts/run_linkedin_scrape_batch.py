#!/usr/bin/env python3
"""Batch-run the LinkedIn browserless scraper for Demo 1 role keywords.

Writes under data/linkedin-exports/<Keyword>/ then optionally ingests into shared_jobs.

Example:
  python scripts/run_linkedin_scrape_batch.py --location India --jobs 100 --posts 15
  python scripts/run_linkedin_scrape_batch.py --keywords "Data Scientist" "GenAI Engineer" --ingest --user-id user_test_1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRAPER = ROOT / "scripts" / "linkedin_browserless_scraper.py"
DEFAULT_KEYWORDS = [
    "Data Scientist",
    "Data Analyst",
    "Analytics Engineer",
    "Machine Learning Engineer",
    "Applied Scientist",
    "MLOps Engineer",
    "GenAI Engineer",
    "LLM Engineer",
    "AI Engineer",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
    parser.add_argument("--location", default="India")
    parser.add_argument("--jobs", type=int, default=100)
    parser.add_argument("--posts", type=int, default=15)
    parser.add_argument("--output", default=str(ROOT / "data" / "linkedin-exports"))
    parser.add_argument("--session", default="linkedin_session.json")
    parser.add_argument("--skip-scrape", action="store_true", help="Only ingest existing exports")
    parser.add_argument("--ingest", action="store_true", help="Upsert into shared_jobs after scrape")
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--no-posts", action="store_true")
    args = parser.parse_args()

    if not args.skip_scrape:
        for keyword in args.keywords:
            cmd = [
                sys.executable,
                str(SCRAPER),
                "--query",
                keyword,
                "--location",
                args.location,
                "--limit",
                str(args.jobs),
                "--posts-limit",
                str(max(10, min(args.posts, 15))),
                "--output",
                args.output,
                "--session",
                args.session,
            ]
            if not args.no_posts:
                cmd.append("--posts")
            print("Running:", " ".join(cmd), flush=True)
            completed = subprocess.run(cmd, cwd=str(ROOT))
            if completed.returncode != 0:
                print(f"Scraper failed for {keyword} (exit {completed.returncode})", file=sys.stderr)
                return completed.returncode

    if args.ingest:
        if not args.user_id:
            print("--ingest requires --user-id", file=sys.stderr)
            return 2
        sys.path[:0] = [
            str(ROOT / "packages" / "connectors"),
            str(ROOT / "packages" / "policy"),
            str(ROOT / "packages" / "domain"),
            str(ROOT / "apps" / "api"),
        ]
        from jobhunt_api.services.linkedin_master import ingest_linkedin_master

        result = ingest_linkedin_master(
            user_id=args.user_id,
            export_dir=args.output,
            keywords=list(args.keywords),
            preferences=list(args.keywords),
            jobs_per_keyword=args.jobs,
            posts_limit=max(10, min(args.posts, 15)),
            match_user=True,
        )
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
