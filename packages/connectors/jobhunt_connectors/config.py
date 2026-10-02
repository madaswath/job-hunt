import os


def env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def gmail_allowed_labels() -> list[str]:
    raw = os.getenv("GMAIL_ALLOWED_LABELS", "JobAlerts,Jobs")
    return [p.strip() for p in raw.split(",") if p.strip()]
