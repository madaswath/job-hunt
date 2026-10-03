#!/usr/bin/env python3
"""
LinkedIn Browserless Job & Recruiter Post Scraper
Runs over HTTP without launching Chromium.

Offline tool only: writes results.json + clean CSV for Job-hunt master ingest.
Job-hunt never runs LinkedIn login itself; drop exports under data/linkedin-exports/.

Features:
- Guest job search + detail enrichment ("About the job")
- Hiring-post filter for recruiter feed posts
- Clean CSV + results.json shaped for AI / Job-hunt ingest
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 is required. Run: pip install beautifulsoup4")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOG = logging.getLogger("linkedin_http")

BASE_URL = "https://www.linkedin.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_job_details(raw_desc: str, criteria_list: list | None = None) -> dict:
    """Isolate pure 'About the job' text and metadata from LinkedIn description."""
    if not raw_desc:
        return {
            "about_job": "",
            "workplace_type": "",
            "employment_type": "",
            "seniority_level": "",
            "job_function": "",
            "industries": "",
        }

    desc = raw_desc.strip()
    desc = re.sub(r"(?i)Show more\s*Show less", "", desc)
    desc = re.sub(r"(?i)\b\d+[\d,]*\s+followers\b", "", desc)
    desc = re.sub(r"(?i)See\s+how\s+you\s+compare\s+to\s+\d+\s+applicants.*", "", desc, flags=re.DOTALL)
    desc = re.sub(r"(?i)Referrals\s+increase\s+your\s+chances.*", "", desc, flags=re.DOTALL)
    desc = re.sub(r"(?i)Get\s+notified\s+about\s+similar\s+jobs.*", "", desc, flags=re.DOTALL)
    desc = re.sub(r"(?i)About\s+the\s+company.*", "", desc, flags=re.DOTALL)

    meta = {
        "workplace_type": "",
        "employment_type": "",
        "seniority_level": "",
        "job_function": "",
        "industries": "",
    }
    if criteria_list:
        for item in criteria_list:
            t = item.lower()
            if any(w in t for w in ["full-time", "part-time", "contract", "internship", "temporary"]):
                meta["employment_type"] = item
            elif any(w in t for w in ["remote", "hybrid", "on-site", "onsite"]):
                meta["workplace_type"] = item
            elif any(w in t for w in ["entry level", "mid-senior", "associate", "director", "executive", "internship"]):
                meta["seniority_level"] = item

    desc = re.sub(r"\n{3,}", "\n\n", desc).strip()
    return {"about_job": desc, **meta}


def generate_recruiter_email(author: str, headline: str, post_content: str, query: str) -> dict:
    """Draft a neutral outreach shell. Job-hunt ingest strips email_draft; keep contact_email only."""
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", post_content)
    contact_email = email_match.group(0) if email_match else ""
    first_name = author.split()[0] if author and author != "LinkedIn Member" else "Hiring Team"
    subject = f"Application: {query} — referencing your LinkedIn post"
    body = (
        f"Hi {first_name},\n\n"
        f"I saw your LinkedIn post about {query} opportunities and wanted to introduce myself.\n\n"
        f"[Insert 2–3 verified facts from your Job-hunt profile / CV here]\n\n"
        f"Happy to share a tailored resume if useful.\n\n"
        f"Best regards,\n"
    )
    return {
        "contact_email": contact_email,
        "email_subject": subject,
        "email_draft": body,
    }


def http_get(url: str, headers: dict | None = None, cookie_str: str | None = None) -> str:
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)
    if cookie_str:
        req_headers["Cookie"] = cookie_str
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def search_jobs_http(query: str, location: str, limit: int = 10) -> list:
    jobs = []
    start = 0
    LOG.info("Searching jobs over HTTP for: '%s' in '%s'...", query, location)
    while len(jobs) < limit and start < 1000:
        params = urllib.parse.urlencode({"keywords": query, "location": location, "start": start})
        url = f"{BASE_URL}/jobs-guest/jobs/api/seeMoreJobPostings/search?{params}"
        try:
            html = http_get(url)
        except Exception as exc:
            LOG.warning("Failed to fetch job search page at start=%d: %s", start, exc)
            break
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li")
        if not cards:
            break
        for card in cards:
            title_el = card.find("h3", class_=re.compile(r"base-search-card__title"))
            comp_el = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
            loc_el = card.find("span", class_=re.compile(r"job-search-card__location"))
            link_el = card.find("a", class_=re.compile(r"base-card__full-link"))
            time_el = card.find("time")
            title = title_el.get_text(strip=True) if title_el else ""
            company = comp_el.get_text(strip=True) if comp_el else ""
            loc = loc_el.get_text(strip=True) if loc_el else ""
            job_url = link_el.get("href", "").split("?")[0] if link_el else ""
            posted_text = time_el.get_text(strip=True) if time_el else ""
            job_id_match = re.search(r"-(\d+)(?:$|\?)", job_url) or re.search(r"/view/(\d+)", job_url)
            job_id = job_id_match.group(1) if job_id_match else ""
            if not title or not job_id:
                continue
            loc_l = loc.lower()
            workplace = "On-site" if "onsite" in loc_l or "on-site" in loc_l else ("Remote" if "remote" in loc_l else "Hybrid / Not Specified")
            jobs.append(
                {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": job_url,
                    "posted_text": posted_text,
                    "posted_at": posted_text,
                    "workplace_type": workplace,
                    "employment_type": "Full-time",
                    "about_job": "",
                    "description": "",
                    "applicants": "",
                    "application_urls": [job_url] if job_url else [],
                    "keyword": query,
                }
            )
            if len(jobs) >= limit:
                break
        start += len(cards)
        time.sleep(0.5)
    LOG.info("Found %d job postings via HTTP search.", len(jobs))
    return jobs[:limit]


def enrich_job_http(job: dict) -> dict:
    job_id = job.get("job_id")
    if not job_id:
        return job
    url = f"{BASE_URL}/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        html = http_get(url)
        soup = BeautifulSoup(html, "html.parser")
        desc_el = soup.find("div", class_=re.compile(r"show-more-less-html__markup|decoratedJobPosting"))
        raw_desc = desc_el.get_text("\n", strip=True) if desc_el else ""
        criteria_els = soup.find_all("li", class_=re.compile(r"description__job-criteria-item"))
        criteria_texts = [c.get_text(" ", strip=True) for c in criteria_els]
        app_el = soup.find("figcaption", class_=re.compile(r"num-applicants|topcard__flavor--metadata"))
        applicants = app_el.get_text(strip=True) if app_el else ""
        cleaned = clean_job_details(raw_desc, criteria_texts)
        job["about_job"] = cleaned["about_job"]
        job["description"] = raw_desc
        if cleaned["workplace_type"]:
            job["workplace_type"] = cleaned["workplace_type"]
        if cleaned["employment_type"]:
            job["employment_type"] = cleaned["employment_type"]
        if cleaned["seniority_level"]:
            job["seniority"] = cleaned["seniority_level"]
        if applicants:
            job["applicants"] = applicants
    except Exception as exc:
        LOG.warning("Failed to enrich job %s: %s", job_id, exc)
    return job


def fetch_single_post_http(urn: str) -> dict | None:
    urn_clean = urn.split(":")[-1]
    candidate_urls = (
        [
            f"{BASE_URL}/embed/feed/update/urn:li:activity:{urn_clean}",
            f"{BASE_URL}/embed/feed/update/urn:li:ugcPost:{urn_clean}",
            f"{BASE_URL}/embed/feed/update/urn:li:share:{urn_clean}",
        ]
        if not urn.startswith("urn:")
        else [f"{BASE_URL}/embed/feed/update/{urn}"]
    )
    html = None
    final_urn = urn
    for embed_url in candidate_urls:
        try:
            html = http_get(embed_url)
            if html and len(html) > 1000:
                final_urn = embed_url.split("/")[-1]
                break
        except Exception:
            continue
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        author_link = soup.find("a", href=re.compile(r"trk=public_post_embed_feed-actor-name")) or soup.find(
            "a", href=re.compile(r"/in/")
        )
        author = author_link.get_text(strip=True) if author_link else ""
        profile_url = author_link["href"].split("?")[0] if author_link else ""
        desc_el = soup.find("p", class_=re.compile(r"feed-shared-text|attributed-text")) or soup.find(
            "div", class_=re.compile(r"feed-shared-text|attributed-text")
        )
        content = desc_el.get_text("\n", strip=True) if desc_el else ""
        if not content:
            for tag in soup.find_all(["p", "div"]):
                t = tag.get_text("\n", strip=True)
                if len(t) > 50 and not any(k in t.lower() for k in ["cookie", "privacy", "sign in", "join now"]):
                    content = t
                    break
        if not author:
            title_text = soup.title.string if soup.title else ""
            if "|" in title_text:
                author = title_text.split("|")[-1].strip()
        time_el = soup.find("time") or soup.find("span", class_=re.compile(r"sub-description|actor__sub-description"))
        posted_time = time_el.get_text(strip=True) if time_el else "Recently"
        post_url = f"{BASE_URL}/feed/update/{final_urn}/"
        if content and len(content) > 25:
            return {
                "post_id": final_urn,
                "author": author or "LinkedIn Member",
                "headline": f"Talent / Hiring Post ({final_urn})",
                "title": f"Talent / Hiring Post ({final_urn})",
                "posted_time": posted_time,
                "posted_at": posted_time,
                "author_profile": profile_url,
                "content": content,
                "url": post_url,
            }
    except Exception as exc:
        LOG.warning("Failed to parse post %s over HTTP: %s", urn, exc)
    return None


def is_hiring_post(text: str, query: str = "") -> tuple[bool, str]:
    if not text or len(text) < 30:
        return False, "Content too short"
    t = text.lower()
    non_hiring_patterns = [
        r"completed.*?(certificate|certification|assessment|test|course)",
        r"proud to share.*?(certificate|assessment|score|completion)",
        r"happy to share that i have successfully completed",
        r"certificate of completion",
        r"quiz of the day",
        r"day \d+\s*/\s*\d+",
        r"exploring python bugs",
        r"python trick",
        r"puzzle of the day",
        r"solved the problem",
        r"score:\s*\d+",
        r"percentage:\s*\d+",
        r"rank:\s*\d+",
        r"#assessment\b",
        r"#quiz\b",
    ]
    for pat in non_hiring_patterns:
        if re.search(pat, t) and not any(
            k in t
            for k in [
                "we are hiring",
                "open role",
                "send resume to",
                "share cv to",
                "looking for candidates",
                "drop your cv",
            ]
        ):
            return False, f"Non-hiring student/test post ({pat})"
    hiring_signals = [
        "hiring",
        "we are hiring",
        "we're hiring",
        "urgent requirement",
        "immediate requirement",
        "job opening",
        "open position",
        "open positions",
        "send resume",
        "share resume",
        "share cv",
        "send cv",
        "drop your cv",
        "drop your resume",
        "interested candidates",
        "apply here",
        "apply at",
        "mail your resume",
        "mail your cv",
        "send profile",
        "share profile",
        "c2c",
        "w2 opportunity",
        "c2h",
        "contract duration",
        "notice period:",
        "ctc:",
        "salary:",
        "years of exp",
        "yrs of exp",
        "#hiring",
        "#jobopening",
        "#urgentrequirement",
        "#careers",
    ]
    matched_signals = [s for s in hiring_signals if s in t]
    query_terms = [w.lower() for w in query.split() if len(w) > 2]
    has_query_term = any(term in t for term in query_terms) if query_terms else True
    if len(matched_signals) >= 1 and has_query_term:
        return True, f"Valid hiring post ({matched_signals})"
    return False, f"Insufficient hiring signals ({matched_signals})"


def search_posts_http(query: str, limit: int = 6, cookie_str: str | None = None) -> list:
    targeted_query = (
        f'"{query}" (hiring OR "looking for" OR "job opening" OR "share resume" OR "send cv" OR "urgently hiring")'
    )
    LOG.info("Searching targeted hiring posts over HTTP for: '%s'...", query)
    posts = []
    params = urllib.parse.urlencode({"keywords": targeted_query, "sortBy": '"date_posted"'})
    url = f"{BASE_URL}/search/results/content/?{params}"
    try:
        html = http_get(url, cookie_str=cookie_str)
        activity_ids = list(dict.fromkeys(re.findall(r"urn:li:activity:(\d+)", html)))
        ugc_ids = list(dict.fromkeys(re.findall(r"urn:li:ugcPost:(\d+)", html)))
        all_urns = [f"urn:li:activity:{aid}" for aid in activity_ids] + [f"urn:li:ugcPost:{uid}" for uid in ugc_ids]
        LOG.info("Found %d post URNs. Checking hiring relevance...", len(all_urns))
        seen = set()
        for urn in all_urns:
            if len(posts) >= limit:
                break
            post_data = fetch_single_post_http(urn)
            if not post_data:
                continue
            content = post_data.get("content", "")
            is_valid, reason = is_hiring_post(content, query)
            if not is_valid:
                LOG.info("Skipping post %s: %s", urn, reason)
                continue
            key = post_data["url"] or content[:80]
            if key in seen:
                continue
            seen.add(key)
            draft = generate_recruiter_email(post_data["author"], post_data["headline"], content, query)
            post_data["contact_email"] = draft["contact_email"]
            post_data["emails"] = [draft["contact_email"]] if draft["contact_email"] else []
            post_data["email_subject"] = draft["email_subject"]
            post_data["email_draft"] = draft["email_draft"]
            post_data["keyword"] = query
            LOG.info("Matched hiring post by %s: %s", post_data["author"], reason)
            posts.append(post_data)
            time.sleep(0.3)
    except Exception as exc:
        LOG.warning("HTTP post search encountered an issue: %s", exc)
    LOG.info("Collected %d verified role hiring posts via HTTP.", len(posts))
    return posts[:limit]


def export_excel_and_csv(run_dir: Path, jobs: list, posts: list, *, query: str) -> None:
    clean_jobs = []
    for j in jobs:
        clean_jobs.append(
            {
                "Job Title": j.get("title", ""),
                "Company": j.get("company", ""),
                "Location": j.get("location", ""),
                "Workplace Type": j.get("workplace_type", ""),
                "Employment Type": j.get("employment_type", ""),
                "Posted Date": j.get("posted_text", ""),
                "Applicants": j.get("applicants", ""),
                "Job URL": j.get("url", ""),
                "About the Job": j.get("about_job", j.get("description", "")),
                "Job ID": j.get("job_id", ""),
                "Application URLs": (
                    json.dumps(j.get("application_urls", []), ensure_ascii=False)
                    if isinstance(j.get("application_urls"), list)
                    else str(j.get("application_urls", ""))
                ),
                "keyword": j.get("keyword") or query,
            }
        )
    clean_posts = []
    for p in posts:
        clean_posts.append(
            {
                "Recruiter / Author": p.get("author", ""),
                "Headline": p.get("headline", ""),
                "Contact Email": p.get("contact_email", ""),
                "Posted Time": p.get("posted_time", ""),
                "Drafted Email Subject": p.get("email_subject", ""),
                "Drafted Email Body": p.get("email_draft", ""),
                "Post URL": p.get("url", ""),
                "Profile URL": p.get("author_profile", ""),
                "Full Post Content": p.get("content", ""),
                "keyword": p.get("keyword") or query,
            }
        )

    def write_csv(path: Path, rows: list) -> None:
        if not rows:
            return
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

    write_csv(run_dir / "jobs_clean.csv", clean_jobs)
    if clean_posts:
        write_csv(run_dir / "recruiter_posts_drafts.csv", clean_posts)
        write_csv(run_dir / "posts.clean.csv", clean_posts)

    try:
        import pandas as pd

        excel_path = run_dir / "jobs.xlsx"
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            if clean_jobs:
                pd.DataFrame(clean_jobs).to_excel(writer, sheet_name="Jobs", index=False)
            if clean_posts:
                pd.DataFrame(clean_posts).to_excel(writer, sheet_name="Recruiter Post Drafts", index=False)
        LOG.info("Saved formatted Excel file to %s", excel_path.resolve())
    except Exception as exc:
        LOG.warning("Excel export failed (%s), CSV files are preserved.", exc)

    results = {
        "metadata": {
            "engine": "browserless_http",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "keyword": query,
            "job_count": len(jobs),
            "post_count": len(posts),
        },
        "jobs": jobs,
        "posts": posts,
    }
    with (run_dir / "results.json").open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    # Stable names for Job-hunt drop folder ingest
    with (run_dir / "jobs.json").open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def scrape_keyword(
    query: str,
    *,
    location: str,
    job_limit: int,
    post_limit: int,
    depth: int,
    cookie_str: str | None,
    output_dir: Path,
    fetch_posts: bool,
) -> Path:
    run_dir = output_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    jobs = search_jobs_http(query, location, job_limit)
    if depth >= 2:
        for idx, job in enumerate(jobs, 1):
            LOG.info("Reading job details %d/%d (ID %s)...", idx, len(jobs), job.get("job_id"))
            enrich_job_http(job)
            time.sleep(0.3)
    posts = search_posts_http(query, limit=post_limit, cookie_str=cookie_str) if fetch_posts else []
    export_excel_and_csv(run_dir, jobs, posts, query=query)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Browserless Fast HTTP Scraper")
    parser.add_argument("--query", default="Data Scientist", help="Search keyword / role")
    parser.add_argument("--location", default="India", help="Location")
    parser.add_argument("--limit", type=int, default=100, help="Number of jobs to scrape (Demo 1 default 100)")
    parser.add_argument("--posts-limit", type=int, default=15, help="Hiring posts to collect (10–15)")
    parser.add_argument("--depth", type=int, default=2, help="Enrichment depth (2=full description)")
    parser.add_argument("--posts", action="store_true", help="Scrape recruiter/user hiring feed posts")
    parser.add_argument(
        "--output",
        default="data/linkedin-exports",
        help="Output root (writes <root>/<query>/ for Job-hunt ingest)",
    )
    parser.add_argument("--session", default="linkedin_session.json", help="Saved session cookies JSON")
    parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Write under a UTC timestamp subfolder instead of overwriting the keyword folder",
    )
    args = parser.parse_args()

    cookie_str = None
    session_path = Path(args.session)
    if session_path.exists():
        try:
            data = json.loads(session_path.read_text(encoding="utf-8"))
            cookies = {c["name"]: c["value"] for c in data.get("cookies", [])}
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            LOG.info("Loaded session cookies from %s", session_path.name)
        except Exception as exc:
            LOG.warning("Could not parse session cookies: %s", exc)

    safe_query = re.sub(r"[\\/]+", " ", args.query).strip() or "general"
    root = Path(args.output)
    if args.timestamped:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_dir = root / safe_query / stamp
    else:
        run_dir = root / safe_query

    start_time = time.time()
    post_limit = max(10, min(int(args.posts_limit), 15))
    scrape_keyword(
        args.query,
        location=args.location,
        job_limit=max(1, args.limit),
        post_limit=post_limit,
        depth=args.depth,
        cookie_str=cookie_str,
        output_dir=run_dir,
        fetch_posts=args.posts,
    )
    LOG.info("Completed in %.2f seconds! Output saved to: %s", time.time() - start_time, run_dir.resolve())


if __name__ == "__main__":
    main()
