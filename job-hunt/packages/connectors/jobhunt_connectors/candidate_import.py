"""Candidate-controlled browserless export ingestion.

This connector deliberately accepts an already-created export.  It never makes
requests to LinkedIn, never accepts browser cookies, and never sends a message.
"""

from typing import Any

from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.normalize import normalize_capture

_FORBIDDEN_FIELD_PARTS = ("cookie", "session", "password", "authorization", "bearer", "email_draft", "generated_email")


def _safe_raw(value: Any) -> Any:
    """Defence in depth for worker calls that do not originate at the HTTP route."""
    if isinstance(value, dict):
        return {key: _safe_raw(child) for key, child in value.items() if not any(part in key.lower() for part in _FORBIDDEN_FIELD_PARTS)}
    if isinstance(value, list):
        return [_safe_raw(child) for child in value]
    return value


class CandidateImportConnector:
    id = "candidate_import"
    slug = "candidate-import"
    status = "live"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary="Candidate-uploaded browserless exports only. No server-side LinkedIn requests, cookie handling, auto-apply, or auto-send.",
            requires_explicit_consent=True,
            max_requests_per_hour=12,
            allowed_operations=["candidate_import", "ingest", "health"],
            forbidden_operations=["scrape", "scrape_authenticated", "store_session_cookie", "send_email", "submit_application"],
            retention_days=180,
            data_classification="candidate_initiated_capture",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(capture_kinds=["job_listing", "hiring_post"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "connected", "method": "candidate_upload"}

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        export = query.get("export") or {}
        metadata = _safe_raw(export.get("metadata") or {})
        target_titles = [str(title).casefold() for title in query.get("titles") or [] if str(title).strip()]
        target_cities = [str(city).casefold() for city in query.get("cities") or [] if str(city).strip()]
        items: list[RawCapture] = []
        for unsafe_job in export.get("jobs") or []:
            job = _safe_raw(unsafe_job)
            title = str(job.get("title") or "").casefold()
            location = str(job.get("location") or "").casefold()
            if target_titles and not any(target in title for target in target_titles):
                continue
            if target_cities and "remote" not in str(job.get("workplace_type") or "").casefold() and not any(city in location for city in target_cities):
                continue
            items.append(
                RawCapture.model_validate(
                    {
                        "connector_id": self.id,
                        "capture_kind": "job_listing",
                        "external_id": str(job.get("job_id") or "") or None,
                        "source_url": job.get("url"),
                        "company": job.get("company"),
                        "title": job.get("title"),
                        "location": job.get("location"),
                        "excerpt": job.get("about_job") or job.get("description") or "",
                        "description": job.get("description") or job.get("about_job") or "",
                        "extracted_apply_urls": job.get("application_urls") or ([job["url"]] if job.get("url") else []),
                        "capture_method": "candidate_browserless_import",
                        "posted_at": job.get("posted_at") or job.get("posted_text"),
                        "work_mode": job.get("workplace_type"),
                        "employment_type": job.get("employment_type"),
                        "source_trusted": False,
                        "raw": {"source_metadata": metadata, "job": job},
                    }
                )
            )
        for unsafe_post in export.get("posts") or []:
            post = _safe_raw(unsafe_post)
            content = post.get("content") or ""
            author = post.get("author") or "Unknown author"
            searchable = f"{post.get('title') or ''} {content}".casefold()
            if target_titles and not any(target in searchable for target in target_titles):
                continue
            items.append(
                RawCapture.model_validate(
                    {
                        "connector_id": self.id,
                        "capture_kind": "hiring_post",
                        "external_id": str(post.get("post_id") or post.get("urn") or "") or None,
                        "source_url": post.get("url"),
                        "company": post.get("company"),
                        "title": post.get("title") or f"Hiring post by {author}",
                        "location": post.get("location") or post.get("author_profile"),
                        "excerpt": content,
                        "description": content,
                        "author": author,
                        "extracted_emails": post.get("emails") or post.get("extracted_emails") or [],
                        "extracted_apply_urls": post.get("apply_urls") or post.get("application_urls") or [],
                        "capture_method": "candidate_browserless_import",
                        "posted_at": post.get("posted_at"),
                        "source_trusted": False,
                        "raw": {"source_metadata": metadata, "post": post},
                    }
                )
            )
        return items

    def normalize(self, raw: RawCapture):
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "immutable_candidate_capture", "hash": item.content_hash}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected"}

    def health(self) -> dict[str, Any]:
        return {"status": "live", "mode": "candidate_upload_only"}
