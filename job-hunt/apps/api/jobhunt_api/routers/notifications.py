from fastapi import APIRouter, Depends
from pydantic import BaseModel

from jobhunt_api import db
from jobhunt_api.auth import current_user

router = APIRouter(tags=["notifications"])


class PrefsIn(BaseModel):
    email_enabled: bool = True
    in_app_enabled: bool = True
    scan_complete: bool = True
    follow_up_reminders: bool = True


@router.get("/notifications")
def list_notes(user: dict = Depends(current_user)) -> dict:
    notes = db.fetch_all("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 50", (user["user_id"],))
    prefs = db.fetch_one("SELECT * FROM notification_preferences WHERE user_id = %s", (user["user_id"],))
    return {"notifications": notes, "preferences": prefs}


@router.put("/notifications/preferences")
def put_prefs(body: PrefsIn, user: dict = Depends(current_user)) -> dict:
    db.execute(
        """
        INSERT INTO notification_preferences (user_id, email_enabled, in_app_enabled, scan_complete, follow_up_reminders)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
          email_enabled = EXCLUDED.email_enabled,
          in_app_enabled = EXCLUDED.in_app_enabled,
          scan_complete = EXCLUDED.scan_complete,
          follow_up_reminders = EXCLUDED.follow_up_reminders
        """,
        (user["user_id"], body.email_enabled, body.in_app_enabled, body.scan_complete, body.follow_up_reminders),
    )
    return list_notes(user)
