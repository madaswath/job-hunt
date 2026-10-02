import hashlib
import json
from urllib.parse import urlparse, urlunparse

from jobhunt_connectors.contract import NormalizedItem, RawCapture


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean).rstrip("/")


def content_hash(raw: RawCapture) -> str:
    payload = {
        "title": (raw.title or "").lower().strip(),
        "company": (raw.company or "").lower().strip(),
        "location": (raw.location or "").lower().strip(),
        "url": canonical_url(raw.source_url),
        "external_id": raw.external_id,
        "excerpt": (raw.excerpt or raw.description or "")[:500],
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def normalize_capture(raw: RawCapture) -> NormalizedItem:
    kind = "hiring_post" if raw.capture_kind == "hiring_post" else "job"
    return NormalizedItem(
        kind=kind,
        capture=raw,
        canonical_url=canonical_url(raw.source_url),
        content_hash=content_hash(raw),
    )
