#!/usr/bin/env python3
"""Ingest LinkedIn scraper JSON/CSV exports into the shared master jobs index.

Usage:
  python scripts/ingest_linkedin_export.py --dir data/linkedin-exports
  python scripts/ingest_linkedin_export.py --dir /path/to/exports --jobs-per-keyword 100 --posts-limit 15

Does not call LinkedIn. Drop files your scraper already wrote, then run this.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "packages" / "connectors"),
    str(ROOT / "packages" / "policy"),
    str(ROOT / "packages" / "domain"),
    str(ROOT / "apps" / "api"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=os.getenv("LINKEDIN_EXPORT_DIR", "data/linkedin-exports"))
    parser.add_argument("--jobs-per-keyword", type=int, default=100)
    parser.add_argument("--posts-limit", type=int, default=15)
    parser.add_argument("--keywords", nargs="*", default=[])
    parser.add_argument("--skills", nargs="*", default=[])
    parser.add_argument("--user-id", default=os.getenv("JOBHUNT_USER_ID"))
    parser.add_argument("--match", action="store_true", help="Also match into user inbox (requires --user-id + DB)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print caps only; no DB writes")
    args = parser.parse_args()

    from jobhunt_connectors.linkedin_export import load_export_tree, select_feed_posts, select_recent_jobs

    root = Path(args.dir)
    bundles = load_export_tree(root)
    summary = []
    for bundle in bundles:
        keyword = (bundle.get("metadata") or {}).get("keyword")
        if args.keywords and keyword and keyword not in args.keywords:
            continue
        jobs = select_recent_jobs(bundle.get("jobs") or [], limit=args.jobs_per_keyword)
        posts = select_feed_posts(
            bundle.get("posts") or [],
            skills=args.skills,
            preferences=args.keywords or ([keyword] if keyword else []),
            limit=args.posts_limit,
        )
        summary.append({"keyword": keyword, "jobs": len(jobs), "posts": len(posts)})

    print(json.dumps({"export_dir": str(root), "bundles": summary}, indent=2))
    if args.dry_run or not args.user_id:
        if not args.user_id:
            print("Pass --user-id (and DATABASE_URL) to write shared_jobs + optional inbox match.", file=sys.stderr)
        return 0

    from jobhunt_api.services.linkedin_master import ingest_linkedin_master

    result = ingest_linkedin_master(
        user_id=args.user_id,
        export_dir=str(root),
        keywords=args.keywords,
        skills=args.skills,
        preferences=args.keywords,
        jobs_per_keyword=args.jobs_per_keyword,
        posts_limit=args.posts_limit,
        match_user=args.match,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
