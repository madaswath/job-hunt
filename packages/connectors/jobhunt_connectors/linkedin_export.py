"""Parse LinkedIn scrape exports (JSON + clean CSV) into normalized job/post dicts.

Expected drop layouts (any one works):

1. Single JSON file:
   { "metadata": { "keyword": "Data Scientist", "engine": "..." },
     "jobs": [ {...} ], "posts": [ {...} ] }

2. Directory per keyword:
   data/linkedin-exports/Data Scientist/jobs.json|jobs.clean.csv
                         posts.json|posts.clean.csv

3. Flat CSV with a `keyword` / `search_keyword` column.

The platform never runs LinkedIn login; it only reads files your scraper already wrote.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

JOB_FILE_NAMES = (
    "jobs.json",
    "results.json",
    "jobs.clean.json",
    "jobs.clean.csv",
    "jobs_clean.csv",
    "jobs.csv",
    "linkedin_jobs.json",
    "linkedin_jobs.csv",
)
POST_FILE_NAMES = (
    "posts.json",
    "posts.clean.json",
    "posts.clean.csv",
    "posts.csv",
    "recruiter_posts_drafts.csv",
    "feed_posts.json",
    "feed_posts.csv",
    "linkedin_posts.json",
    "linkedin_posts.csv",
)

_JOB_ALIASES = {
    "job_id": ("job_id", "id", "linkedin_job_id", "jobid", "external_id", "Job ID"),
    "title": ("title", "job_title", "role", "position", "Job Title"),
    "company": ("company", "company_name", "employer", "Company"),
    "location": ("location", "job_location", "city", "Location"),
    "url": ("url", "job_url", "link", "source_url", "canonical_url", "Job URL"),
    "description": (
        "description",
        "about_job",
        "job_description",
        "jd",
        "full_description",
        "About the Job",
    ),
    "posted_at": (
        "posted_at",
        "date_posted",
        "posted",
        "posted_date",
        "posted_text",
        "listed_at",
        "Posted Date",
    ),
    "workplace_type": ("workplace_type", "work_mode", "remote_type", "work_type", "Workplace Type"),
    "employment_type": ("employment_type", "job_type", "employment", "Employment Type"),
    "seniority": ("seniority", "level", "experience_level", "seniority_level"),
    "skills": ("skills", "skillset", "required_skills"),
    "emails": ("emails", "extracted_emails", "recruiter_email", "email", "Contact Email"),
    "apply_urls": ("application_urls", "apply_urls", "apply_url", "Application URLs"),
    "keyword": ("keyword", "search_keyword", "query", "search_query", "role_keyword"),
    "applicants": ("applicants", "Applicants"),
}

_POST_ALIASES = {
    "post_id": ("post_id", "id", "urn", "activity_id", "external_id"),
    "author": ("author", "author_name", "poster", "author_profile", "Recruiter / Author"),
    "content": ("content", "text", "post_text", "body", "description", "Full Post Content"),
    "title": ("title", "headline", "Headline"),
    "company": ("company", "company_name"),
    "location": ("location", "author_location"),
    "url": ("url", "post_url", "link", "source_url", "Post URL"),
    "emails": ("emails", "extracted_emails", "email", "contact_email", "Contact Email"),
    "apply_urls": ("apply_urls", "application_urls"),
    "posted_at": ("posted_at", "posted", "date_posted", "created_at", "posted_time", "Posted Time"),
    "keyword": ("keyword", "search_keyword", "query"),
    "author_profile": ("author_profile", "Profile URL", "profile_url"),
}

# Never ingest scraper-generated outreach copy into matching / facts.
_STRIP_KEYS = ("email_draft", "email_subject", "drafted email body", "drafted email subject")


def _strip_generated(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in row.items():
        lowered = str(key).strip().lower()
        if any(part in lowered for part in _STRIP_KEYS):
            continue
        out[key] = value
    return out


def _normalize_employment(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    text = re.sub(r"(?i)^employment\s*type\s*", "", text).strip()
    lowered = text.casefold()
    for token in ("full-time", "part-time", "contract", "internship", "temporary"):
        if token in lowered:
            return token
    return text


def _normalize_workplace(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    lowered = text.casefold()
    if "remote" in lowered:
        return "remote"
    if "hybrid" in lowered:
        return "hybrid"
    if "on-site" in lowered or "onsite" in lowered or "on site" in lowered:
        return "onsite"
    return text


def _pick(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for name in aliases:
        key = str(name).strip().lower()
        if key in lower and lower[key] not in (None, ""):
            return lower[key]
    return None


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in re.split(r"[|;,]", text) if part.strip()]


def _parse_posted_at(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    candidates = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    cleaned = text.replace("+00:00", "Z")
    for fmt in candidates:
        try:
            return datetime.strptime(cleaned, fmt).isoformat()
        except ValueError:
            continue
    return text


def normalize_job_row(row: dict[str, Any], *, default_keyword: str | None = None) -> dict[str, Any]:
    row = _strip_generated(row)
    skills = _as_list(_pick(row, _JOB_ALIASES["skills"]))
    emails = _as_list(_pick(row, _JOB_ALIASES["emails"]))
    apply_urls = _as_list(_pick(row, _JOB_ALIASES["apply_urls"]))
    url = _pick(row, _JOB_ALIASES["url"])
    if url and str(url) not in apply_urls:
        apply_urls = [str(url), *apply_urls]
    keyword = _pick(row, _JOB_ALIASES["keyword"]) or default_keyword
    about = _pick(row, _JOB_ALIASES["description"]) or ""
    return {
        "job_id": str(_pick(row, _JOB_ALIASES["job_id"]) or "") or None,
        "title": _pick(row, _JOB_ALIASES["title"]),
        "company": _pick(row, _JOB_ALIASES["company"]),
        "location": _pick(row, _JOB_ALIASES["location"]),
        "url": url,
        "description": about,
        "about_job": about,
        "posted_at": _parse_posted_at(_pick(row, _JOB_ALIASES["posted_at"])),
        "workplace_type": _normalize_workplace(_pick(row, _JOB_ALIASES["workplace_type"])),
        "employment_type": _normalize_employment(_pick(row, _JOB_ALIASES["employment_type"])),
        "seniority": _pick(row, _JOB_ALIASES["seniority"]),
        "skills": skills,
        "emails": emails,
        "application_urls": apply_urls,
        "keyword": keyword,
        "applicants": _pick(row, _JOB_ALIASES["applicants"]),
    }


def normalize_post_row(row: dict[str, Any], *, default_keyword: str | None = None) -> dict[str, Any]:
    row = _strip_generated(row)
    emails = _as_list(_pick(row, _POST_ALIASES["emails"]))
    # Pull emails from content if Contact Email missing
    content = str(_pick(row, _POST_ALIASES["content"]) or "")
    if not emails:
        found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content)
        emails = found[:3]
    return {
        "post_id": str(_pick(row, _POST_ALIASES["post_id"]) or "") or None,
        "author": _pick(row, _POST_ALIASES["author"]),
        "content": content,
        "title": _pick(row, _POST_ALIASES["title"]),
        "company": _pick(row, _POST_ALIASES["company"]),
        "location": _pick(row, _POST_ALIASES["location"]),
        "url": _pick(row, _POST_ALIASES["url"]),
        "emails": emails,
        "apply_urls": _as_list(_pick(row, _POST_ALIASES["apply_urls"])),
        "posted_at": _parse_posted_at(_pick(row, _POST_ALIASES["posted_at"])),
        "keyword": _pick(row, _POST_ALIASES["keyword"]) or default_keyword,
        "author_profile": _pick(row, _POST_ALIASES["author_profile"]),
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _rows_from_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Return (jobs, posts, keyword_hint)."""
    suffix = path.suffix.lower()
    keyword_hint = path.stem
    if suffix == ".json":
        data = _load_json(path)
        if isinstance(data, list):
            # Heuristic: feed-like if content/author dominate
            if data and ("content" in data[0] or "post_id" in data[0] or "author" in data[0]):
                return [], data, None
            return data, [], None
        if isinstance(data, dict):
            meta = data.get("metadata") or {}
            kw = meta.get("keyword") or meta.get("search_keyword") or data.get("keyword")
            jobs = data.get("jobs") or data.get("job_listings") or []
            posts = data.get("posts") or data.get("feed_posts") or data.get("hiring_posts") or []
            if not jobs and not posts and ("title" in data or "job_title" in data):
                jobs = [data]
            return list(jobs), list(posts), kw
        return [], [], None
    if suffix == ".csv":
        rows = _load_csv(path)
        name = path.name.lower()
        if "post" in name or "feed" in name:
            return [], rows, keyword_hint
        return rows, [], keyword_hint
    return [], [], None


def load_export_path(path: Path, *, default_keyword: str | None = None) -> dict[str, Any]:
    path = Path(path)
    jobs_raw: list[dict[str, Any]] = []
    posts_raw: list[dict[str, Any]] = []
    keyword = default_keyword

    if path.is_file():
        j, p, kw = _rows_from_file(path)
        jobs_raw.extend(j)
        posts_raw.extend(p)
        keyword = keyword or kw
    elif path.is_dir():
        keyword = keyword or path.name
        matched_named = False
        for name in JOB_FILE_NAMES + POST_FILE_NAMES:
            candidate = path / name
            if candidate.exists():
                matched_named = True
                j, p, kw = _rows_from_file(candidate)
                jobs_raw.extend(j)
                posts_raw.extend(p)
                keyword = keyword or kw
        if not matched_named:
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() in {".json", ".csv"}:
                    j, p, kw = _rows_from_file(child)
                    jobs_raw.extend(j)
                    posts_raw.extend(p)
                    keyword = keyword or kw
    else:
        raise FileNotFoundError(str(path))

    jobs = [normalize_job_row(row, default_keyword=keyword) for row in jobs_raw if isinstance(row, dict)]
    posts = [normalize_post_row(row, default_keyword=keyword) for row in posts_raw if isinstance(row, dict)]
    jobs = [j for j in jobs if j.get("title") or j.get("url")]
    posts = [p for p in posts if p.get("content") or p.get("url")]
    return {
        "metadata": {"keyword": keyword, "source_path": str(path)},
        "jobs": jobs,
        "posts": posts,
    }


def load_export_tree(root: Path) -> list[dict[str, Any]]:
    """Load one export bundle per keyword directory, or a single root bundle."""
    root = Path(root)
    if not root.exists():
        return []
    if root.is_file():
        return [load_export_path(root)]

    bundles: list[dict[str, Any]] = []
    subdirs = [p for p in sorted(root.iterdir()) if p.is_dir()]
    files = [p for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in {".json", ".csv"}]

    if subdirs:
        for sub in subdirs:
            bundles.append(load_export_path(sub, default_keyword=sub.name))
        return bundles

    if files:
        # Prefer one merged bundle when the root looks like a single export set.
        if len(files) <= 4:
            return [load_export_path(root)]
        by_keyword: dict[str, list[Path]] = {}
        for file in files:
            key = file.stem
            for token in ("jobs.clean", "posts.clean", "feed_posts", "linkedin_jobs", "linkedin_posts", "jobs", "posts", "clean"):
                key = key.replace(token, "")
            key = key.strip("._- ") or "general"
            by_keyword.setdefault(key, []).append(file)
        for key, group in by_keyword.items():
            merged_jobs: list[dict[str, Any]] = []
            merged_posts: list[dict[str, Any]] = []
            for file in group:
                part = load_export_path(file, default_keyword=key)
                merged_jobs.extend(part["jobs"])
                merged_posts.extend(part["posts"])
            bundles.append(
                {
                    "metadata": {"keyword": key, "source_path": str(root)},
                    "jobs": merged_jobs,
                    "posts": merged_posts,
                }
            )
    return bundles


def select_recent_jobs(jobs: list[dict[str, Any]], *, limit: int = 100) -> list[dict[str, Any]]:
    def sort_key(job: dict[str, Any]):
        posted = job.get("posted_at") or ""
        return str(posted)

    ordered = sorted(jobs, key=sort_key, reverse=True)
    return ordered[: max(0, limit)]


def select_feed_posts(
    posts: list[dict[str, Any]],
    *,
    skills: list[str] | None = None,
    preferences: list[str] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    needles = [s.casefold() for s in (skills or []) + (preferences or []) if s and str(s).strip()]
    scored: list[tuple[int, dict[str, Any]]] = []
    for post in posts:
        blob = f"{post.get('title') or ''} {post.get('content') or ''} {post.get('company') or ''}".casefold()
        score = sum(1 for n in needles if n in blob) if needles else 1
        if needles and score == 0:
            continue
        scored.append((score, post))
    scored.sort(key=lambda item: (item[0], str(item[1].get("posted_at") or "")), reverse=True)
    # Prefer 10–15 window: clamp to requested limit (default 15)
    return [post for _, post in scored[: max(0, limit)]]
