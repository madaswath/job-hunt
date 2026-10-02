import json

from jobhunt_api import db


def record(user_id: str, action: str, resource_type: str | None = None, resource_id: str | None = None, metadata: dict | None = None) -> None:
    db.execute(
        """
        INSERT INTO audit_events (user_id, action, resource_type, resource_id, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        """,
        (user_id, action, resource_type, resource_id, json.dumps(metadata or {})),
    )
