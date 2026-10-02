import httpx

from jobhunt_api import db
from jobhunt_api.settings import settings


def _storage_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def delete_storage_paths(paths: list[str]) -> dict[str, int]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return {"deleted": 0, "skipped": len(paths)}
    bucket = settings.supabase_storage_bucket
    deleted = 0
    skipped = 0
    base = settings.supabase_url.rstrip("/")
    with httpx.Client(timeout=30) as client:
        for path in paths:
            if not path:
                skipped += 1
                continue
            res = client.delete(f"{base}/storage/v1/object/{bucket}/{path.lstrip('/')}", headers=_storage_headers())
            if res.status_code in {200, 204, 404}:
                deleted += 1
            else:
                skipped += 1
    return {"deleted": deleted, "skipped": skipped}


def collect_user_storage_paths(user_id: str) -> list[str]:
    rows = db.fetch_all(
        """
        SELECT storage_path FROM resumes WHERE user_id = %s AND storage_path IS NOT NULL
        UNION ALL
        SELECT storage_path FROM resume_versions WHERE user_id = %s AND storage_path IS NOT NULL
        """,
        (user_id, user_id),
    )
    return [r["storage_path"] for r in rows if r.get("storage_path")]
