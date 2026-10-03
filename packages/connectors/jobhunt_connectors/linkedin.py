"""LinkedIn jobs connector for Demo 1.

Ingests:
- recorded fixtures
- scraper export drops (JSON + clean CSV) from LINKEDIN_EXPORT_DIR / query.export_dir
- inline export payloads (jobs + posts)

Does not perform authenticated LinkedIn login, cookie replay, or unrestricted live scraping.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jobhunt_connectors.config import env_flag
from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.linkedin_export import (
    load_export_path,
    load_export_tree,
    select_feed_posts,
    select_recent_jobs,
)
from jobhunt_connectors.normalize import normalize_capture

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "linkedin" / "postings.json"
DEFAULT_EXPORT_DIR = Path(__file__).resolve().parents[3] / "data" / "linkedin-exports"

# Bump when ingest behavior changes.
LINKEDIN_CONNECTOR_VERSION = "2026-10-03-demo1-export-master-v2"


def _default_export_dir() -> Path:
    return Path(os.getenv("LINKEDIN_EXPORT_DIR") or DEFAULT_EXPORT_DIR)


def _job_to_capture(job: dict[str, Any], *, keyword: str | None) -> RawCapture:
    return RawCapture.model_validate(
        {
            "connector_id": "linkedin",
            "capture_kind": "job_listing",
            "external_id": job.get("job_id"),
            "source_url": job.get("url"),
            "company": job.get("company"),
            "title": job.get("title"),
            "location": job.get("location"),
            "excerpt": (job.get("about_job") or job.get("description") or "")[:500],
            "description": job.get("description") or job.get("about_job") or "",
            "extracted_emails": job.get("emails") or [],
            "extracted_apply_urls": job.get("application_urls") or [],
            "capture_method": "linkedin_scraper_export",
            "posted_at": job.get("posted_at"),
            "skills": job.get("skills") or [],
            "must_have_skills": (job.get("skills") or [])[:5],
            "work_mode": job.get("workplace_type"),
            "employment_type": job.get("employment_type"),
            "seniority": job.get("seniority"),
            "source_trusted": False,
            "raw": {"keyword": keyword or job.get("keyword"), "job": job},
        }
    )


def _post_to_capture(post: dict[str, Any], *, keyword: str | None) -> RawCapture:
    author = post.get("author") or "Unknown author"
    return RawCapture.model_validate(
        {
            "connector_id": "linkedin",
            "capture_kind": "hiring_post",
            "external_id": post.get("post_id"),
            "source_url": post.get("url"),
            "company": post.get("company"),
            "title": post.get("title") or f"Hiring post by {author}",
            "location": post.get("location"),
            "excerpt": (post.get("content") or "")[:500],
            "description": post.get("content") or "",
            "author": author,
            "extracted_emails": post.get("emails") or [],
            "extracted_apply_urls": post.get("apply_urls") or [],
            "capture_method": "linkedin_scraper_export",
            "posted_at": post.get("posted_at"),
            "source_trusted": False,
            "raw": {"keyword": keyword or post.get("keyword"), "post": post},
        }
    )


class LinkedInJobsConnector:
    id = "linkedin"
    slug = "linkedin"
    status = "ingestion_ready"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary=(
                "Ingests LinkedIn-shaped scraper export files (JSON/CSV) and fixtures into the shared master index. "
                "No authenticated session, no cookie store, no auto-apply/send. "
                "Unrestricted live scrape remains forbidden; drop files from your offline scraper."
            ),
            requires_explicit_consent=True,
            max_requests_per_hour=30,
            allowed_operations=["connect", "ingest", "normalize", "revoke", "health"],
            forbidden_operations=[
                "send_email",
                "submit_application",
                "scrape_authenticated",
                "unrestricted_scrape",
                "store_session_cookie",
            ],
            retention_days=90,
            data_classification="marketplace_derived_export",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(can_search=True, capture_kinds=["job_listing", "hiring_post"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "connected",
            "method": "export_drop_consent",
            "user_id": ctx.get("user_id"),
            "export_dir": str(_default_export_dir()),
            "scrape_enabled": env_flag("FEATURE_LINKEDIN_SCRAPE", False),
        }

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        from jobhunt_policy.source_matrix import assert_acquisition_allowed

        assert_acquisition_allowed(self.id, "recorded_scrape_fixture")
        if query.get("mode") == "unrestricted_scrape" or query.get("use_live_scrape"):
            assert_acquisition_allowed(self.id, "unrestricted_scrape")

        jobs_per_keyword = int(query.get("jobs_per_keyword") or 100)
        raw_posts_limit = query.get("posts_limit")
        posts_limit = int(raw_posts_limit) if raw_posts_limit is not None else 15
        posts_limit = max(0, min(posts_limit, 50))
        skills = [str(s) for s in (query.get("skills") or ctx.get("skills") or []) if str(s).strip()]
        preferences = [str(s) for s in (query.get("preferences") or query.get("titles") or []) if str(s).strip()]
        keyword_filter = {str(k).casefold() for k in (query.get("keywords") or []) if str(k).strip()}

        captures: list[RawCapture] = []

        # 1) Inline export payload (API upload)
        if query.get("export"):
            export = query["export"]
            keyword = (export.get("metadata") or {}).get("keyword")
            jobs = select_recent_jobs(export.get("jobs") or [], limit=jobs_per_keyword)
            posts = select_feed_posts(export.get("posts") or [], skills=skills, preferences=preferences, limit=posts_limit)
            captures.extend(_job_to_capture(job, keyword=keyword) for job in jobs)
            captures.extend(_post_to_capture(post, keyword=keyword) for post in posts)
            return captures

        # 2) Export directory from scraper drop
        export_dir = query.get("export_dir") or ctx.get("export_dir") or os.getenv("LINKEDIN_EXPORT_DIR")
        if export_dir or query.get("use_export_dir"):
            root = Path(export_dir) if export_dir else _default_export_dir()
            if root.exists():
                for bundle in load_export_tree(root):
                    keyword = (bundle.get("metadata") or {}).get("keyword")
                    if keyword_filter and keyword and str(keyword).casefold() not in keyword_filter:
                        continue
                    jobs = select_recent_jobs(bundle.get("jobs") or [], limit=jobs_per_keyword)
                    posts = select_feed_posts(
                        bundle.get("posts") or [],
                        skills=skills,
                        preferences=preferences,
                        limit=posts_limit,
                    )
                    captures.extend(_job_to_capture(job, keyword=keyword) for job in jobs)
                    captures.extend(_post_to_capture(post, keyword=keyword) for post in posts)
                if captures:
                    return captures

        # 3) Single file path
        if query.get("export_path"):
            bundle = load_export_path(Path(query["export_path"]))
            keyword = (bundle.get("metadata") or {}).get("keyword")
            jobs = select_recent_jobs(bundle.get("jobs") or [], limit=jobs_per_keyword)
            posts = select_feed_posts(bundle.get("posts") or [], skills=skills, preferences=preferences, limit=posts_limit)
            captures.extend(_job_to_capture(job, keyword=keyword) for job in jobs)
            captures.extend(_post_to_capture(post, keyword=keyword) for post in posts)
            return captures

        # 4) Legacy RawCapture fixture list
        path = Path(query.get("fixture_path") or ctx.get("fixture_path") or FIXTURE_PATH)
        if not path.exists():
            return []
        items = json.loads(path.read_text())
        titles = {str(t).lower() for t in (query.get("titles") or []) if str(t).strip()}
        cities = {str(c).lower() for c in (query.get("cities") or []) if str(c).strip()}
        for item in items:
            title = str(item.get("title") or "")
            location = str(item.get("location") or "")
            work_mode = str(item.get("work_mode") or "").lower()
            if titles and not any(t in title.lower() for t in titles):
                continue
            if cities and "remote" not in work_mode and location.lower() not in cities and not any(c in location.lower() for c in cities):
                continue
            captures.append(
                RawCapture.model_validate(
                    {
                        **item,
                        "connector_id": self.id,
                        "capture_kind": item.get("capture_kind") or "job_listing",
                        "capture_method": item.get("capture_method") or "linkedin_recorded_scrape",
                        "source_trusted": bool(item.get("source_trusted", False)),
                    }
                )
            )
        return captures[: jobs_per_keyword + posts_limit]

    def normalize(self, raw: RawCapture):
        if raw.capture_method in {"scrape_authenticated", "unrestricted_scrape"}:
            raise PermissionError("linkedin connector forbids authenticated/unrestricted scrape captures")
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "unchanged", "hash": getattr(item, "content_hash", None)}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected", "user_id": ctx.get("user_id")}

    def health(self) -> dict[str, Any]:
        export_dir = _default_export_dir()
        return {
            "status": self.status,
            "connector_version": LINKEDIN_CONNECTOR_VERSION,
            "fixture_exists": FIXTURE_PATH.exists(),
            "export_dir": str(export_dir),
            "export_dir_exists": export_dir.exists(),
            "feature_linkedin_scrape": env_flag("FEATURE_LINKEDIN_SCRAPE", False),
            "production_live": False,
        }
