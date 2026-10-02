import base64
import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from jobhunt_connectors.gmail_failures import GmailFailureKind, GmailIngestError, classify_http_status

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
URL_RE = re.compile(r"https?://[^\s<>\"']+")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _request_with_backoff(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    max_attempts: int = 4,
) -> httpx.Response:
    delay = 1.0
    for attempt in range(max_attempts):
        res = client.request(method, url, headers=headers)
        if res.status_code < 400:
            return res
        kind = classify_http_status(res.status_code, res.text)
        if kind in {GmailFailureKind.TRANSIENT, GmailFailureKind.RATE_LIMIT} and attempt < max_attempts - 1:
            retry_after = int(res.headers.get("retry-after", delay))
            time.sleep(min(retry_after, 30))
            delay = min(delay * 2, 30)
            continue
        raise GmailIngestError(kind, f"Gmail API {res.status_code}: {res.text[:200]}", retry_after=delay)
    raise GmailIngestError(GmailFailureKind.TRANSIENT, "Gmail API retries exhausted")


def _label_query(labels: list[str]) -> str:
    parts = [f"label:{quote(label)}" for label in labels if label]
    return " OR ".join(parts) if parts else "label:JobAlerts"


def _decode_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"] + "==").decode(errors="ignore")
    for part in payload.get("parts") or []:
        text = _decode_body(part)
        if text:
            return text
    return ""


def _parse_message(msg: dict, labels: list[str]) -> dict[str, Any]:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    snippet = msg.get("snippet") or ""
    body = _decode_body(msg.get("payload") or {}) or snippet
    text = f"{subject}\n{body}"
    apply_urls = list(dict.fromkeys(URL_RE.findall(text)))[:10]
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))[:5]
    internal = msg.get("internalDate")
    posted_at = None
    if internal:
        posted_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(internal) / 1000))
    return {
        "external_id": msg["id"],
        "source_url": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
        "title": subject[:200] or "Job alert",
        "company": None,
        "location": None,
        "excerpt": snippet[:500],
        "description": body[:8000],
        "extracted_emails": emails,
        "extracted_apply_urls": apply_urls,
        "labels": labels,
        "posted_at": posted_at,
    }


def fetch_labeled_messages(
    access_token: str,
    labels: list[str],
    *,
    max_messages: int = 25,
    page_token: str | None = None,
    seen_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    seen = seen_ids or set()
    collected: list[dict[str, Any]] = []
    next_token = page_token
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=30) as client:
        while len(collected) < max_messages:
            q = _label_query(labels)
            list_url = f"{GMAIL_API}/messages?q={quote(q)}&maxResults={min(50, max_messages)}"
            if next_token:
                list_url += f"&pageToken={quote(next_token)}"
            list_res = _request_with_backoff(client, "GET", list_url, headers=headers)
            data = list_res.json()
            for ref in data.get("messages") or []:
                mid = ref["id"]
                if mid in seen:
                    continue
                seen.add(mid)
                msg_res = _request_with_backoff(client, "GET", f"{GMAIL_API}/messages/{mid}?format=full", headers=headers)
                collected.append(_parse_message(msg_res.json(), labels))
                if len(collected) >= max_messages:
                    break
            next_token = data.get("nextPageToken")
            if not next_token or len(collected) >= max_messages:
                break
    return collected, next_token
